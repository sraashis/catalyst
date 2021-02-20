# flake8: noqa

from typing import Any, Dict, List
import logging
from tempfile import TemporaryDirectory

from pytest import mark
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from catalyst.callbacks import CheckpointCallback, CriterionCallback, OptimizerCallback
from catalyst.core.callback import Callback, CallbackOrder
from catalyst.core.runner import IRunner
from catalyst.engines import DataParallelEngine
from catalyst.engines.device import DeviceEngine
from catalyst.loggers import ConsoleLogger, CSVLogger
from catalyst.registry import REGISTRY
from catalyst.settings import IS_CUDA_AVAILABLE, NUM_CUDA_DEVICES

from .misc import DummyDataset, DummyModel, LossMinimizationCallback

logger = logging.getLogger(__name__)


class CustomRunner(IRunner):
    _logdir = "./logdir"

    def get_engine(self):
        return DataParallelEngine()

    def get_loggers(self):
        return {
            "console": ConsoleLogger(),
            "csv": CSVLogger(logdir=self._logdir),
        }

    @property
    def stages(self) -> List[str]:
        return ["train"]

    def get_stage_len(self, stage: str) -> int:
        return 10

    def get_loaders(self, stage: str, epoch: int = None) -> Dict[str, Any]:
        dataset = DummyDataset(6)
        loader = DataLoader(dataset, batch_size=4)
        return {"train": loader, "valid": loader}

    def get_model(self, stage: str):
        return DummyModel(4, 2)

    def get_criterion(self, stage: str):
        return nn.MSELoss()

    def get_optimizer(self, stage: str, model):
        return optim.SGD(model.parameters(), lr=1e-3)

    def get_scheduler(self, stage: str, optimizer):
        return None

    def get_callbacks(self, stage: str):
        return {
            "criterion": CriterionCallback(
                metric_key="loss", input_key="logits", target_key="targets"
            ),
            "optimizer": OptimizerCallback(metric_key="loss"),
            # "scheduler": dl.SchedulerCallback(loader_key="valid", metric_key="loss"),
            "checkpoint": CheckpointCallback(
                self._logdir, loader_key="valid", metric_key="loss", minimize=True, save_n_best=3
            ),
            # "check": DeviceCheckCallback(),
            "check2": LossMinimizationCallback("loss"),
        }

    def handle_batch(self, batch):
        x, y = batch
        logits = self.model(x)

        self.batch = {
            "features": x,
            "targets": y,
            "logits": logits,
        }


def run_train_with_experiment_parallel_device():
    # dataset = DummyDataset(10)
    # loader = DataLoader(dataset, batch_size=4)
    # runner = SupervisedRunner()
    # exp = Experiment(
    #     model=_model_fn,
    #     criterion=nn.MSELoss(),
    #     optimizer=_optimizer_fn,
    #     loaders={"train": loader, "valid": loader},
    #     main_metric="loss",
    #     callbacks=[
    #         CriterionCallback(),
    #         OptimizerCallback(),
    #         # DeviceCheckCallback(device),
    #         LossMinimizationCallback(),
    #     ],
    #     engine=DataParallelEngine(),
    # )
    with TemporaryDirectory() as logdir:
        runner = CustomRunner()
        runner._logdir = logdir
        runner.run()


def run_train_with_config_experiment_parallel_device():
    pass
    # dataset = DummyDataset(10)
    # runner = SupervisedRunner()
    # logdir = f"./test_dp_engine"
    # exp = ConfigExperiment(
    #     config={
    #         "model_params": {"_target_": "DummyModel", "in_features": 4, "out_features": 1,},
    #         "engine": "dp",
    #         "args": {"logdir": logdir},
    #         "stages": {
    #             "data_params": {"batch_size": 4, "num_workers": 0},
    #             "criterion_params": {"_target_": "MSELoss"},
    #             "optimizer_params": {"_target_": "SGD", "lr": 1e-3},
    #             "stage1": {
    #                 "stage_params": {"num_epochs": 2},
    #                 "callbacks_params": {
    #                     "loss": {"_target_": "CriterionCallback"},
    #                     "optimizer": {"_target_": "OptimizerCallback"},
    #                     # "test_device": {
    #                     #     "_target_": "DeviceCheckCallback",
    #                     #     "assert_device": str(device),
    #                     # },
    #                     "test_loss_minimization": {"callback": "LossMinimizationCallback"},
    #                 },
    #             },
    #         },
    #     }
    # )
    # exp.get_datasets = lambda *args, **kwargs: {
    #     "train": dataset,
    #     "valid": dataset,
    # }
    # runner.run(exp)
    # shutil.rmtree(logdir, ignore_errors=True)


@mark.skipif(not IS_CUDA_AVAILABLE, reason="CUDA device is not available")
def test_experiment_parallel_engine_with_cuda():
    run_train_with_experiment_parallel_device()


@mark.skip("Config experiment is in development phase!")
@mark.skipif(not IS_CUDA_AVAILABLE, reason="CUDA device is not available")
def test_config_experiment_engine_with_cuda():
    run_train_with_config_experiment_parallel_device()
