"""
Homography computation and validation.

Computes geometric transformations between coordinate systems and validates quality.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from models import Point2D, HomographyMatrix, CalibrationQuality


def compute_homography(
    source_points: List[Point2D],
    dest_points: List[Point2D],
    ransac_threshold: float = 5.0
) -> Tuple[HomographyMatrix, np.ndarray, CalibrationQuality]:
    """
    Compute homography matrix from point correspondences.

    Args:
        source_points: Points in source coordinate system (e.g., camera)
        dest_points: Corresponding points in destination system (e.g., projector)
        ransac_threshold: RANSAC reprojection threshold in pixels

    Returns:
        Tuple of:
        - homography: HomographyMatrix object
        - inlier_mask: Boolean mask indicating which points were inliers
        - quality: CalibrationQuality metrics

    Raises:
        ValueError: If insufficient points or homography computation fails
    """
    if len(source_points) != len(dest_points):
        raise ValueError(
            f"Point count mismatch: {len(source_points)} source vs "
            f"{len(dest_points)} destination"
        )

    if len(source_points) < 4:
        raise ValueError(
            f"Need at least 4 point pairs, got {len(source_points)}"
        )

    # Convert Point2D lists to numpy arrays
    src_pts = np.array([[p.x, p.y] for p in source_points], dtype=np.float32)
    dst_pts = np.array([[p.x, p.y] for p in dest_points], dtype=np.float32)

    # Compute homography with RANSAC
    H, mask = cv2.findHomography(
        src_pts,
        dst_pts,
        cv2.RANSAC,
        ransacReprojThreshold=ransac_threshold
    )

    if H is None:
        raise ValueError("Failed to compute homography. Points may be degenerate.")

    # Calculate quality metrics
    quality = _compute_quality_metrics(
        src_pts,
        dst_pts,
        H,
        mask
    )

    # Convert to HomographyMatrix
    homography = HomographyMatrix.from_numpy(H)

    return homography, mask, quality


def _compute_quality_metrics(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    H: np.ndarray,
    inlier_mask: np.ndarray
) -> CalibrationQuality:
    """
    Compute quality metrics for homography.

    Args:
        src_pts: Source points (Nx2)
        dst_pts: Destination points (Nx2)
        H: 3x3 homography matrix
        inlier_mask: Boolean mask for inliers

    Returns:
        CalibrationQuality object
    """
    # Project source points through homography
    src_pts_homog = np.column_stack([src_pts, np.ones(len(src_pts))])
    projected_homog = (H @ src_pts_homog.T).T

    # Convert from homogeneous coordinates
    projected = projected_homog[:, :2] / projected_homog[:, 2:3]

    # Compute reprojection errors
    errors = np.linalg.norm(projected - dst_pts, axis=1)

    # Overall metrics
    rms_error = np.sqrt(np.mean(errors ** 2))
    max_error = np.max(errors)

    # Inlier metrics
    num_inliers = int(np.sum(inlier_mask))
    num_total = len(src_pts)
    inlier_ratio = num_inliers / num_total if num_total > 0 else 0.0

    return CalibrationQuality(
        reprojection_error_rms=float(rms_error),
        reprojection_error_max=float(max_error),
        num_inliers=num_inliers,
        num_total_points=num_total,
        inlier_ratio=inlier_ratio
    )


def apply_homography(
    H: HomographyMatrix,
    points: List[Point2D]
) -> List[Point2D]:
    """
    Apply homography transformation to points.

    Args:
        H: Homography matrix
        points: List of points to transform

    Returns:
        Transformed points
    """
    if not points:
        return []

    # Convert to numpy
    H_np = H.to_numpy()
    pts = np.array([[p.x, p.y] for p in points], dtype=np.float32)

    # Reshape for perspectiveTransform (needs Nx1x2)
    pts_reshaped = pts.reshape(-1, 1, 2)

    # Apply transformation
    transformed = cv2.perspectiveTransform(pts_reshaped, H_np)

    # Convert back to Point2D list
    result = [
        Point2D(x=float(pt[0][0]), y=float(pt[0][1]))
        for pt in transformed
    ]

    return result


def apply_homography_single(
    H: HomographyMatrix,
    point: Point2D
) -> Point2D:
    """
    Apply homography transformation to a single point.

    Args:
        H: Homography matrix
        point: Point to transform

    Returns:
        Transformed point
    """
    result = apply_homography(H, [point])
    return result[0]


def validate_homography(
    H: HomographyMatrix,
    test_point_pairs: List[Tuple[Point2D, Point2D]],
    threshold: float = 3.0
) -> Tuple[bool, dict]:
    """
    Validate homography quality using test point pairs.

    Args:
        H: Homography to validate
        test_point_pairs: List of (source, expected_dest) pairs
        threshold: Maximum acceptable error in pixels

    Returns:
        Tuple of (is_valid, metrics_dict)
    """
    if not test_point_pairs:
        return True, {"error": "No test points provided"}

    source_points = [pair[0] for pair in test_point_pairs]
    expected_points = [pair[1] for pair in test_point_pairs]

    # Transform source points
    transformed = apply_homography(H, source_points)

    # Calculate errors
    errors = []
    for transformed_pt, expected_pt in zip(transformed, expected_points):
        dx = transformed_pt.x - expected_pt.x
        dy = transformed_pt.y - expected_pt.y
        error = np.sqrt(dx**2 + dy**2)
        errors.append(error)

    # Compute metrics
    rms_error = np.sqrt(np.mean(np.array(errors) ** 2))
    max_error = np.max(errors)
    is_valid = rms_error < threshold

    metrics = {
        "rms_error": float(rms_error),
        "max_error": float(max_error),
        "mean_error": float(np.mean(errors)),
        "num_test_points": len(test_point_pairs),
        "threshold": threshold,
        "is_valid": is_valid
    }

    return is_valid, metrics


def compute_inverse_homography(H: HomographyMatrix) -> HomographyMatrix:
    """
    Compute inverse homography.

    Useful for bidirectional transformations (e.g., Camera→Projector and Projector→Camera).

    Args:
        H: Homography matrix

    Returns:
        Inverse homography matrix
    """
    H_np = H.to_numpy()
    H_inv = np.linalg.inv(H_np)
    return HomographyMatrix.from_numpy(H_inv)


if __name__ == "__main__":
    # Example usage with synthetic data
    print("Testing homography computation...")

    # Create synthetic point correspondences (identity transformation)
    source_points = [
        Point2D(x=100, y=100),
        Point2D(x=500, y=100),
        Point2D(x=500, y=400),
        Point2D(x=100, y=400),
        Point2D(x=300, y=250),
    ]

    # Add small perturbation to simulate real-world noise
    dest_points = [
        Point2D(x=102, y=99),
        Point2D(x=501, y=101),
        Point2D(x=499, y=402),
        Point2D(x=101, y=399),
        Point2D(x=301, y=251),
    ]

    # Compute homography
    H, mask, quality = compute_homography(
        source_points,
        dest_points,
        ransac_threshold=5.0
    )

    print(f"\nQuality metrics:")
    print(f"  RMS error: {quality.reprojection_error_rms:.2f} pixels")
    print(f"  Max error: {quality.reprojection_error_max:.2f} pixels")
    print(f"  Inliers: {quality.num_inliers}/{quality.num_total_points}")
    print(f"  Inlier ratio: {quality.inlier_ratio:.2%}")
    print(f"  Is acceptable: {quality.is_acceptable}")

    # Test forward and inverse transformation
    test_point = Point2D(x=300, y=300)
    transformed = apply_homography_single(H, test_point)
    print(f"\nTransform test:")
    print(f"  Original: ({test_point.x:.1f}, {test_point.y:.1f})")
    print(f"  Transformed: ({transformed.x:.1f}, {transformed.y:.1f})")

    # Test inverse
    H_inv = compute_inverse_homography(H)
    back_transformed = apply_homography_single(H_inv, transformed)
    print(f"  Back-transformed: ({back_transformed.x:.1f}, {back_transformed.y:.1f})")

    # Validate
    test_pairs = [(source_points[0], dest_points[0])]
    is_valid, metrics = validate_homography(H, test_pairs, threshold=3.0)
    print(f"\nValidation:")
    print(f"  Valid: {is_valid}")
    print(f"  Metrics: {metrics}")
