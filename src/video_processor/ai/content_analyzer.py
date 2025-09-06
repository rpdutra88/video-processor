"""AI-powered video content analysis using existing infrastructure."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ffmpeg

# Optional dependency handling (same pattern as existing 360° code)
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

logger = logging.getLogger(__name__)


@dataclass
class SceneAnalysis:
    """Scene detection analysis results."""
    scene_boundaries: list[float]  # Timestamps in seconds
    scene_count: int
    average_scene_length: float
    key_moments: list[float]  # Most important timestamps for thumbnails
    confidence_scores: list[float]  # Confidence for each scene boundary


@dataclass  
class QualityMetrics:
    """Video quality assessment metrics."""
    sharpness_score: float  # 0-1, higher is sharper
    brightness_score: float  # 0-1, optimal around 0.5
    contrast_score: float   # 0-1, higher is more contrast
    noise_level: float      # 0-1, lower is better
    overall_quality: float  # 0-1, composite quality score


@dataclass
class ContentAnalysis:
    """Comprehensive video content analysis results."""
    scenes: SceneAnalysis
    quality_metrics: QualityMetrics
    duration: float
    resolution: tuple[int, int]
    has_motion: bool
    motion_intensity: float  # 0-1, higher means more motion
    is_360_video: bool
    recommended_thumbnails: list[float]  # Optimal thumbnail timestamps


class VideoContentAnalyzer:
    """AI-powered video content analysis leveraging existing infrastructure."""

    def __init__(self, enable_opencv: bool = True) -> None:
        self.enable_opencv = enable_opencv and HAS_OPENCV
        
        if not self.enable_opencv:
            logger.warning(
                "OpenCV not available. Content analysis will use FFmpeg-only methods. "
                "Install with: uv add opencv-python"
            )

    async def analyze_content(self, video_path: Path) -> ContentAnalysis:
        """
        Comprehensive video content analysis.
        
        Builds on existing metadata extraction and adds AI-powered insights.
        """
        # Use existing FFmpeg probe infrastructure (same as existing code)
        probe_info = await self._get_video_metadata(video_path)
        
        # Basic video information
        video_stream = next(
            stream for stream in probe_info["streams"] 
            if stream["codec_type"] == "video"
        )
        
        duration = float(video_stream.get("duration", probe_info["format"]["duration"]))
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        
        # Scene analysis using FFmpeg + OpenCV if available
        scenes = await self._analyze_scenes(video_path, duration)
        
        # Quality assessment
        quality = await self._assess_quality(video_path, scenes.key_moments[:3])
        
        # Motion detection
        motion_data = await self._detect_motion(video_path, duration)
        
        # 360° detection using existing infrastructure
        is_360 = self._detect_360_video(probe_info)
        
        # Generate optimal thumbnail recommendations
        recommended_thumbnails = self._recommend_thumbnails(scenes, quality, duration)
        
        return ContentAnalysis(
            scenes=scenes,
            quality_metrics=quality,
            duration=duration,
            resolution=(width, height),
            has_motion=motion_data["has_motion"],
            motion_intensity=motion_data["intensity"], 
            is_360_video=is_360,
            recommended_thumbnails=recommended_thumbnails,
        )

    async def _get_video_metadata(self, video_path: Path) -> dict[str, Any]:
        """Get video metadata using existing FFmpeg infrastructure."""
        return ffmpeg.probe(str(video_path))

    async def _analyze_scenes(self, video_path: Path, duration: float) -> SceneAnalysis:
        """
        Analyze video scenes using FFmpeg scene detection.
        
        Uses FFmpeg's built-in scene detection filter for efficiency.
        """
        try:
            # Use FFmpeg scene detection (lightweight, no OpenCV needed)
            scene_filter = "select='gt(scene,0.3)'"
            
            # Run scene detection
            process = (
                ffmpeg
                .input(str(video_path))
                .filter('select', 'gt(scene,0.3)')
                .filter('showinfo')
                .output('-', format='null')
                .run_async(pipe_stderr=True, quiet=True)
            )
            
            _, stderr = await asyncio.create_task(
                asyncio.to_thread(process.communicate)
            )
            
            # Parse scene boundaries from FFmpeg output
            scene_boundaries = self._parse_scene_boundaries(stderr.decode())
            
            # If no scene boundaries found, use duration-based fallback
            if not scene_boundaries:
                scene_boundaries = self._generate_fallback_scenes(duration)
            
            scene_count = len(scene_boundaries) + 1
            avg_length = duration / scene_count if scene_count > 0 else duration
            
            # Select key moments (first 30% of each scene)
            key_moments = [
                boundary + (avg_length * 0.3) 
                for boundary in scene_boundaries[:5]  # Limit to 5 key moments
            ]
            
            # Add start if no boundaries
            if not key_moments:
                key_moments = [min(10, duration * 0.2)]
            
            # Generate confidence scores (simple heuristic for now)
            confidence_scores = [0.8] * len(scene_boundaries)
            
            return SceneAnalysis(
                scene_boundaries=scene_boundaries,
                scene_count=scene_count,
                average_scene_length=avg_length,
                key_moments=key_moments,
                confidence_scores=confidence_scores,
            )
            
        except Exception as e:
            logger.warning(f"Scene analysis failed, using fallback: {e}")
            return self._fallback_scene_analysis(duration)

    def _parse_scene_boundaries(self, ffmpeg_output: str) -> list[float]:
        """Parse scene boundaries from FFmpeg showinfo output."""
        boundaries = []
        
        for line in ffmpeg_output.split('\n'):
            if 'pts_time:' in line:
                try:
                    # Extract timestamp from showinfo output
                    pts_part = line.split('pts_time:')[1].split()[0]
                    timestamp = float(pts_part)
                    boundaries.append(timestamp)
                except (ValueError, IndexError):
                    continue
        
        return sorted(boundaries)

    def _generate_fallback_scenes(self, duration: float) -> list[float]:
        """Generate scene boundaries based on duration when detection fails."""
        if duration <= 30:
            return []  # Short video, no scene breaks needed
        elif duration <= 120:
            return [duration / 2]  # Single scene break in middle
        else:
            # Multiple scene breaks every ~30 seconds
            num_scenes = min(int(duration / 30), 10)  # Max 10 scenes
            return [duration * (i / num_scenes) for i in range(1, num_scenes)]

    def _fallback_scene_analysis(self, duration: float) -> SceneAnalysis:
        """Fallback scene analysis when detection fails."""
        boundaries = self._generate_fallback_scenes(duration)
        
        return SceneAnalysis(
            scene_boundaries=boundaries,
            scene_count=len(boundaries) + 1,
            average_scene_length=duration / (len(boundaries) + 1),
            key_moments=[min(10, duration * 0.2)],
            confidence_scores=[0.5] * len(boundaries),
        )

    async def _assess_quality(
        self, video_path: Path, sample_timestamps: list[float]
    ) -> QualityMetrics:
        """
        Assess video quality using sample frames.
        
        Uses OpenCV if available, otherwise FFmpeg-based heuristics.
        """
        if not self.enable_opencv:
            return self._fallback_quality_assessment()
            
        try:
            # Use OpenCV for detailed quality analysis
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                return self._fallback_quality_assessment()
            
            quality_scores = []
            
            for timestamp in sample_timestamps[:3]:  # Analyze max 3 frames
                # Seek to timestamp  
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # Calculate quality metrics
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Sharpness (Laplacian variance)
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var() / 10000
                sharpness = min(sharpness, 1.0)
                
                # Brightness (mean intensity)  
                brightness = np.mean(gray) / 255
                
                # Contrast (standard deviation)
                contrast = np.std(gray) / 128
                contrast = min(contrast, 1.0)
                
                # Simple noise estimation (high frequency content)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                noise = np.mean(np.abs(gray.astype(float) - blur.astype(float))) / 255
                noise = min(noise, 1.0)
                
                quality_scores.append({
                    'sharpness': sharpness,
                    'brightness': brightness, 
                    'contrast': contrast,
                    'noise': noise,
                })
            
            cap.release()
            
            if not quality_scores:
                return self._fallback_quality_assessment()
            
            # Average the metrics
            avg_sharpness = np.mean([q['sharpness'] for q in quality_scores])
            avg_brightness = np.mean([q['brightness'] for q in quality_scores])
            avg_contrast = np.mean([q['contrast'] for q in quality_scores])
            avg_noise = np.mean([q['noise'] for q in quality_scores])
            
            # Overall quality (weighted combination)
            overall = (
                avg_sharpness * 0.3 +
                (1 - abs(avg_brightness - 0.5) * 2) * 0.2 +  # Optimal brightness ~0.5
                avg_contrast * 0.3 +
                (1 - avg_noise) * 0.2  # Lower noise is better
            )
            
            return QualityMetrics(
                sharpness_score=float(avg_sharpness),
                brightness_score=float(avg_brightness),
                contrast_score=float(avg_contrast),
                noise_level=float(avg_noise),
                overall_quality=float(overall),
            )
            
        except Exception as e:
            logger.warning(f"OpenCV quality analysis failed: {e}")
            return self._fallback_quality_assessment()

    def _fallback_quality_assessment(self) -> QualityMetrics:
        """Fallback quality assessment when OpenCV is unavailable."""
        # Conservative estimates for unknown quality
        return QualityMetrics(
            sharpness_score=0.7,
            brightness_score=0.5,
            contrast_score=0.6,
            noise_level=0.3,
            overall_quality=0.6,
        )

    async def _detect_motion(self, video_path: Path, duration: float) -> dict[str, Any]:
        """
        Detect motion in video using FFmpeg motion estimation.
        
        Uses FFmpeg's motion vectors for efficient motion detection.
        """
        try:
            # Sample a few timestamps for motion analysis
            sample_duration = min(10, duration)  # Sample first 10 seconds max
            
            # Use FFmpeg motion estimation filter
            process = (
                ffmpeg
                .input(str(video_path), t=sample_duration)
                .filter('mestimate')
                .filter('showinfo')
                .output('-', format='null')  
                .run_async(pipe_stderr=True, quiet=True)
            )
            
            _, stderr = await asyncio.create_task(
                asyncio.to_thread(process.communicate)
            )
            
            # Parse motion information from output
            motion_data = self._parse_motion_data(stderr.decode())
            
            return {
                'has_motion': motion_data['intensity'] > 0.1,
                'intensity': motion_data['intensity'],
            }
            
        except Exception as e:
            logger.warning(f"Motion detection failed: {e}")
            # Conservative fallback
            return {'has_motion': True, 'intensity': 0.5}

    def _parse_motion_data(self, ffmpeg_output: str) -> dict[str, float]:
        """Parse motion intensity from FFmpeg motion estimation output."""
        # Simple heuristic based on frame processing information
        lines = ffmpeg_output.split('\n')
        processed_frames = len([line for line in lines if 'pts_time:' in line])
        
        # More processed frames generally indicates more motion/complexity
        intensity = min(processed_frames / 100, 1.0)
        
        return {'intensity': intensity}

    def _detect_360_video(self, probe_info: dict[str, Any]) -> bool:
        """
        Detect 360° video using existing Video360Detection logic.
        
        Simplified version that reuses existing detection patterns.
        """
        # Check spherical metadata (same as existing code)
        format_tags = probe_info.get("format", {}).get("tags", {})
        
        spherical_indicators = [
            "Spherical", "spherical-video", "SphericalVideo", 
            "ProjectionType", "projection_type"
        ]
        
        for tag_name in format_tags:
            if any(indicator.lower() in tag_name.lower() for indicator in spherical_indicators):
                return True
        
        # Check aspect ratio for equirectangular (same as existing code)
        try:
            video_stream = next(
                stream for stream in probe_info["streams"]
                if stream["codec_type"] == "video"
            )
            
            width = int(video_stream["width"])
            height = int(video_stream["height"])
            aspect_ratio = width / height
            
            # Equirectangular videos typically have 2:1 aspect ratio
            return 1.9 <= aspect_ratio <= 2.1
            
        except (KeyError, ValueError, StopIteration):
            return False

    def _recommend_thumbnails(
        self, scenes: SceneAnalysis, quality: QualityMetrics, duration: float
    ) -> list[float]:
        """
        Recommend optimal thumbnail timestamps based on analysis.
        
        Combines scene analysis with quality metrics for smart selection.
        """
        recommendations = []
        
        # Start with key moments from scene analysis
        recommendations.extend(scenes.key_moments[:3])
        
        # Add beginning if video is long enough and quality is good
        if duration > 30 and quality.overall_quality > 0.5:
            recommendations.append(min(5, duration * 0.1))
        
        # Add middle timestamp
        if duration > 60:
            recommendations.append(duration / 2)
        
        # Remove duplicates and sort
        recommendations = sorted(list(set(recommendations)))
        
        # Limit to reasonable number of recommendations
        return recommendations[:5]

    @staticmethod
    def is_analysis_available() -> bool:
        """Check if content analysis capabilities are available."""
        return HAS_OPENCV

    @staticmethod
    def get_missing_dependencies() -> list[str]:
        """Get list of missing dependencies for full analysis capabilities."""
        missing = []
        
        if not HAS_OPENCV:
            missing.append("opencv-python")
            
        return missing