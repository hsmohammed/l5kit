import numpy as np
import pytest

from l5kit.data import ChunkedDataset
from l5kit.dataset import EgoDataset
from l5kit.geometry import agent_pose, rotation33_as_yaw
from l5kit.rasterization import RenderContext, StubRasterizer
from l5kit.sampling.agent_sampling import _create_targets_for_deep_prediction


@pytest.fixture(scope="function")
def base_displacement(zarr_dataset: ChunkedDataset, cfg: dict) -> np.ndarray:
    future_num_frames = cfg["model_params"]["future_num_frames"]
    ref_frame = zarr_dataset.frames[0]
    world_from_agent = agent_pose(ref_frame["ego_translation"][:2], rotation33_as_yaw((ref_frame["ego_rotation"])))

    future_coords_offset, *_ = _create_targets_for_deep_prediction(
        num_frames=future_num_frames,
        frames=zarr_dataset.frames[1 : 1 + future_num_frames],
        selected_track_id=None,
        agents=[np.empty(0) for _ in range(future_num_frames)],
        agent_from_world=np.linalg.inv(world_from_agent),
        current_agent_yaw=rotation33_as_yaw(ref_frame["ego_rotation"]),
    )
    return future_coords_offset


# all these params should not have any effect on the displacement (as it is in world coordinates)
@pytest.mark.parametrize("raster_size", [(100, 100), (100, 50), (200, 200), (50, 50)])
@pytest.mark.parametrize("ego_center", [(0.25, 0.25), (0.75, 0.75), (0.5, 0.5)])
@pytest.mark.parametrize("pixel_size", [(0.25, 0.25), (0.5, 0.5)])
def test_same_displacement(
    cfg: dict,
    zarr_dataset: ChunkedDataset,
    base_displacement: np.ndarray,
    raster_size: tuple,
    ego_center: tuple,
    pixel_size: tuple,
) -> None:
    cfg["raster_params"]["raster_size"] = raster_size
    cfg["raster_params"]["pixel_size"] = np.asarray(pixel_size)
    cfg["raster_params"]["ego_center"] = np.asarray(ego_center)

    render_context = RenderContext(np.asarray(raster_size), np.asarray(pixel_size), np.asarray(ego_center))
    dataset = EgoDataset(cfg, zarr_dataset, StubRasterizer(render_context, 0.5,),)
    data = dataset[0]
    assert np.allclose(data["target_positions"], base_displacement)
