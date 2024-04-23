import argparse
import torch
import os

from ret_benchmark.config import cfg
from ret_benchmark.data import build_data
from ret_benchmark.engine.trainer import do_train
from ret_benchmark.losses import build_loss
from ret_benchmark.modeling import build_model
from ret_benchmark.solver import build_lr_scheduler, build_optimizer
from ret_benchmark.utils.logger import setup_logger
from ret_benchmark.utils.checkpoint import Checkpointer
from tensorboardX import SummaryWriter

import resource

rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (2048, rlimit[1]))


def train(cfg):
    logger = setup_logger(name="Train", level=cfg.LOGGER.LEVEL)
    logger.info(cfg)
    model = build_model(cfg)
    device = torch.device(cfg.MODEL.DEVICE)
    model.to(device)
    if len(os.environ["CUDA_VISIBLE_DEVICES"]) > 1:
        model = torch.nn.DataParallel(model)

    criterion = build_loss(cfg)

    optimizer = build_optimizer(cfg, model)
    scheduler = build_lr_scheduler(cfg, optimizer)

    train_loader = build_data(cfg, is_train=True)
    val_loader = build_data(cfg, is_train=False)

    logger.info(train_loader.dataset)
    for x in val_loader:
        logger.info(x.dataset)

    arguments = dict()
    arguments["iteration"] = 0

    checkpoint_period = cfg.SOLVER.CHECKPOINT_PERIOD
    ckp_save_path = os.path.join(cfg.SAVE_DIR, cfg.NAME)
    os.makedirs(ckp_save_path, exist_ok=True)
    checkpointer = Checkpointer(model, optimizer, scheduler, ckp_save_path)

    tb_save_path = os.path.join(cfg.TB_SAVE_DIR, cfg.NAME)
    os.makedirs(tb_save_path, exist_ok=True)
    writer = SummaryWriter(tb_save_path)

    do_train(
        cfg,
        model,
        train_loader,
        val_loader,
        optimizer,
        scheduler,
        criterion,
        checkpointer,
        writer,
        device,
        checkpoint_period,
        arguments,
        logger,
    )


def parse_args():
    """
  Parse input arguments
  """
    parser = argparse.ArgumentParser(description="Train a retrieval network")
    parser.add_argument(
        "--cfg", dest="cfg_file", help="config file", default=None, type=str
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg.merge_from_file(args.cfg_file)
    train(cfg)
