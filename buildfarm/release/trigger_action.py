import argparse
import json
import logging
import site
import taskcluster
import yaml

from os import path

site.addsitedir(path.join(path.dirname(__file__), "../../lib/python"))

from kickoff.actions import generate_action_task, submit_action_task

log = logging.getLogger(__name__)
SUPPORTED_ACTIONS = ["publish_fennec"]


def get_task(task_id):
    queue = taskcluster.Queue()
    return queue.task(task_id)


def main():
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action-task-id", required=True,
        help="Task ID of the initial action task (promote_fennec or promote_firefox"
    )
    parser.add_argument("--release-runner-config", required=True, type=argparse.FileType('r'),
                        help="Release runner config")
    parser.add_argument("--action-flavor", required=True, choices=SUPPORTED_ACTIONS)
    parser.add_argument("--force", action="store_true", default=False,
                        help="Submit action task without asking")
    args = parser.parse_args()
    release_runner_config = yaml.safe_load(args.release_runner_config)
    tc_config = {
        "credentials": {
            "clientId": release_runner_config["taskcluster"].get("client_id"),
            "accessToken": release_runner_config["taskcluster"].get("access_token"),
        },
        "maxRetries": 12,
    }
    queue = taskcluster.Queue(tc_config)

    task = get_task(args.action_task_id)
    action_input = task["extra"]["action"]["context"]["input"]
    parameters = task["extra"]["action"]["context"]["parameters"]
    action_task_id, action_task = generate_action_task(
            project=parameters["project"],
            revision=parameters["head_rev"],
            next_version=action_input["next_version"],
            build_number=action_input["build_number"],
            release_promotion_flavor=args.action_flavor
    )

    log.info("Submitting action task %s for %s", action_task_id, args.action_flavor)
    log.info("Project: %s", parameters["project"])
    log.info("Revision: %s", parameters["head_rev"])
    log.info("Next version: %s", action_input["next_version"])
    log.info("Build number: %s", action_input["build_number"])
    log.info("Task definition:\n%s", json.dumps(action_task, sort_keys=True, indent=2))
    if not args.force:
        yes_no = raw_input("Submit the task? [y/N]: ")
        if yes_no not in ('y', 'Y'):
            log.info("Not submitting")
            exit(1)

    submit_action_task(queue=queue, action_task_id=action_task_id,
                       action_task=action_task)


if __name__ == "__main__":
    main()