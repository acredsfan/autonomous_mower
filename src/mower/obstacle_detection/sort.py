"""
Simple Online and Realtime Tracking (SORT) with Kalman Filter.

This implementation is adapted from the original SORT algorithm
and is used for object tracking in the autonomous mower project.
It provides a basic framework for tracking objects across frames
using bounding box information.

Original paper: https://arxiv.org/abs/1602.00763
"""

import numpy as np


class KalmanFilter:
    """
    A simple Kalman filter for tracking bounding boxes.

    This class implements a linear Kalman filter to estimate the state
    (position and velocity) of a tracked object based on noisy
    measurements (bounding box detections).
    """

    def __init__(self):
        """Initialize the Kalman filter."""
        ndim, dt = 4, 1.0

        # State transition matrix (predict next state)
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        # Measurement matrix (relate state to measurement)
        self._update_mat = np.eye(ndim, 2 * ndim)

        # Process noise covariance (uncertainty in motion model)
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement):
        """
        Create track from unassociated measurement.

        Args:
            measurement: Initial bounding box [x, y, w, h]

        Returns:
            Mean and covariance of the new track
        """
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean, covariance):
        """
        Run Kalman filter prediction step.

        Args:
            mean: Current state mean
            covariance: Current state covariance

        Returns:
            Predicted state mean and covariance
        """
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        mean = np.dot(self._motion_mat, mean)
        covariance = (
            np.linalg.multi_dot((
                self._motion_mat, covariance, self._motion_mat.T))
            + motion_cov
        )
        return mean, covariance

    def project(self, mean, covariance):
        """
        Project state distribution to measurement space.

        Args:
            mean: Current state mean
            covariance: Current state covariance

        Returns:
            Projected measurement mean and covariance
        """
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        mean = np.dot(self._update_mat, mean)
        covariance = np.linalg.multi_dot((
            self._update_mat, covariance, self._update_mat.T))
        return mean, covariance + innovation_cov

    def update(self, mean, covariance, measurement):
        """
        Run Kalman filter correction step.

        Args:
            mean: Current state mean
            covariance: Current state covariance
            measurement: Bounding box detection [x, y, w, h]

        Returns:
            Updated state mean and covariance
        """
        projected_mean, projected_cov = self.project(mean, covariance)

        chol_factor = np.linalg.cholesky(projected_cov)
        kalman_gain = np.linalg.solve(
            chol_factor, np.linalg.solve(chol_factor.T, np.dot(
                covariance, self._update_mat.T).T)
        ).T
        innovation = measurement - projected_mean

        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot((
            kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance


class Sort:
    """
    Main class for the SORT algorithm.
    """

    def __init__(self):
        """Initialize the tracker."""
        self.max_age = 1
        self.min_hits = 3
        self.trackers = []
        self.frame_count = 0

    def update(self, dets=np.empty((0, 5))):
        """
        Update tracks with detections.

        Args:
            dets: Array of detections [[x1, y1, x2, y2, score], ...]

        Returns:
            Array of tracked objects [[x1, y1, x2, y2, track_id], ...]
        """
        self.frame_count += 1
        # Get predicted locations from existing trackers.
        trks = np.zeros((len(self.trackers), 5))
        to_del = []
        ret = []
        i = 0
        for t in self.trackers:
            pos = t.predict()[0][:4].copy()
            trks[i, :] = [pos[0], pos[1], pos[2], pos[3], 0]
            if np.any(np.isnan(pos)):
                to_del.append(i)
            ret.append(np.concatenate((pos, ([t.id + 1])), axis=0))
            i += 1
        if trks.shape[0] > 0:
            trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
            for t in reversed(to_del):
                self.trackers.pop(t)
        dets_to_trk = np.empty((0, 5))
        if len(self.trackers) == 0:
            dets_to_trk = dets
        else:
            dets_to_trk = dets
        for d in dets_to_trk:
            t = KalmanBoxTracker(d, self.frame_count)
            self.trackers.append(t)
            ret.append(np.concatenate((d[:4], ([t.id + 1])), axis=0))
        i = len(self.trackers)
        for trk in reversed(self.trackers):
            d = trk.update(dets_to_trk, self.frame_count)
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)
            i -= 1
            if d:
                ret.append(np.concatenate((d[:4], ([trk.id + 1])), axis=0))
        if len(ret) > 0:
            return np.stack(ret)
        return np.empty((0, 5))


class KalmanBoxTracker(object):
    """
    This class represents the internal state of individual tracked objects
    observed as bbox.
    """

    count = 0

    def __init__(self, detection, frame_count):
        """
        Initialises a tracker using initial bounding box.
        """
        # define constant velocity model
        self.kf = KalmanFilter()
        # [x1, y1, x2, y2] -> [x, y, w, h]
        x, y, w, h = detection[:4]
        detection[:4] = [(x + w) / 2, (y + h) / 2, w - x, h - y]
        self.mean, self.covariance = self.kf.initiate(detection[:4])
        self.id = self.count
        KalmanBoxTracker.count += 1
        self.hits = 1  # number of total hits including the first detection
        self.time_since_update = 0
        self.history = []
        self.age = 0
        self.max_age = 0
        self.state = 0  # 0 init, 1 confirmed, 2 deleted
        self.time_since_update = 0
        self.update(detection, frame_count)

    def update(self, detection, frame_count):
        """
        Updates the state vector with observed bbox.
        """
        if detection.size > 0:
            self.time_since_update = 0
            # [x1, y1, x2, y2] -> [x, y, w, h]
            x, y, w, h = detection[:4]
            detection[:4] = [(x + w) / 2, (y + h) / 2, w - x, h - y]
            self.mean, self.covariance = self.kf.update(
                self.mean, self.covariance, detection[:4]
            )
            self.hits += 1
        self.age += 1
        if self.state == 0 and self.hits >= 3:
            self.state = 1
            return self.get_state()
        elif self.time_since_update >= self.max_age:
            self.state = 2
            return []
        return self.get_state()

    def predict(self):
        """
        Advances the state vector and returns the predicted bounding box estimate.
        """
        self.mean, self.covariance = self.kf.predict(
            self.mean, self.covariance)
        self.age += 1
        self.time_since_update += 1
        return self.mean, self.covariance

    def get_state(self):
        """
        Returns the current bounding box estimate.
        """
        # [x, y, w, h] -> [x1, y1, x2, y2]
        x, y, a, h = self.mean[:4]
        return [x - a / 2, y - h / 2, x + a / 2, y + h / 2]
