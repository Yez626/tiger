from typing import Any, Dict, List
from uuid import UUID, uuid4

from celery import Task
from celery.exceptions import Reject
from joj.horse_client.models import JudgeCredentials
from loguru import logger

from joj.tiger import errors
from joj.tiger.horse_apis import HorseClient
from joj.tiger.runner import Runner
from joj.tiger.schemas import (
    CompletedCommand,
    ExecuteResult,
    ExecuteStatus,
    SubmitResult,
    SubmitStatus,
)


class TigerTask:
    id: UUID
    task: Task
    record: Dict[str, Any]
    horse_client: HorseClient
    credentials: JudgeCredentials

    def __init__(self, task: Task, record: Dict[str, Any], base_url: str) -> None:
        self.id = uuid4()  # this id should be unique, be used to create docker images
        self.task = task
        self.record = record
        self.horse_client = HorseClient(base_url)
        logger.debug(task)
        logger.debug(record)

    async def update_state(self) -> None:
        self.task.update_state()

    async def login(self) -> None:
        await self.horse_client.login()

    async def claim(self) -> None:
        self.credentials = await self.horse_client.claim_record(
            domain_id=self.record["domain_id"],
            record_id=self.record["id"],
            task_id=self.task.request.id,
        )
        await self.update_state()

    async def fetch_problem_config(self) -> None:
        pass

    async def fetch_record(self) -> None:
        pass

    async def compile(self) -> CompletedCommand:
        with Runner() as runner:
            return runner.run_command(["echo", "hello world"])

    async def execute(self) -> List[ExecuteResult]:
        with Runner() as runner:
            return [
                ExecuteResult(
                    status=ExecuteStatus.accepted,
                    completed_command=runner.run_command(["echo", "hello world"]),
                )
            ]

    async def clean(self) -> None:
        pass

    async def submit(self) -> SubmitResult:
        try:
            # await self.login()
            # await self.claim()
            # await self.fetch_problem_config()
            # await self.fetch_record()
            compile_result = await self.compile()
            execute_results = await self.execute()
            return SubmitResult(
                submit_status=SubmitStatus.accepted,
                compile_result=compile_result,
                execute_results=execute_results,
            )
        except errors.WorkerRejectError:
            raise Reject("WorkerRejectError", requeue=True)
        except errors.RetryableError:
            self.task.retry(countdown=5)
        except Exception as e:
            logger.exception(e)
            # fail the task
            return SubmitResult(submit_status=SubmitStatus.system_error)
        # logger.info(self)
        # logger.info(record_dict)
        # try:
        #     access_token = await get_access_token(base_url)
        #     print(access_token)
        # except Exception as e:
        #     logger.error(e)
        #     logger.info(self.request.delivery_info)
        #     # await asyncio.sleep(5)
        #     # raise Reject("login failed", requeue=True)
        #
        #     self.retry(countdown=1)
        #     await asyncio.sleep(5)
