"""
Video Processor - AI-Enhanced Professional Video Processing Library.

Features comprehensive video processing with 360° support, AI-powered content analysis,
multiple format encoding, intelligent thumbnail generation, and background processing.
"""

from .config import ProcessorConfig
from .core.processor import VideoProcessor, VideoProcessingResult
from .exceptions import (
    EncodingError,
    FFmpegError, 
    StorageError,
    ValidationError,
    VideoProcessorError,
)

# Optional 360° imports
try:
    from .core.thumbnails_360 import Thumbnail360Generator
    from .utils.video_360 import HAS_360_SUPPORT, Video360Detection, Video360Utils
except ImportError:
    HAS_360_SUPPORT = False

# Optional AI imports  
try:
    from .ai import ContentAnalysis, SceneAnalysis, VideoContentAnalyzer
    from .core.enhanced_processor import EnhancedVideoProcessor, EnhancedVideoProcessingResult
    HAS_AI_SUPPORT = True
except ImportError:
    HAS_AI_SUPPORT = False

__version__ = "0.3.0"
__all__ = [
    "VideoProcessor",
    "VideoProcessingResult",
    "ProcessorConfig", 
    "VideoProcessorError",
    "ValidationError",
    "StorageError",
    "EncodingError",
    "FFmpegError",
    "HAS_360_SUPPORT",
]

# Add 360° exports if available
if HAS_360_SUPPORT:
    __all__.extend([
        "Video360Detection",
        "Video360Utils", 
        "Thumbnail360Generator",
    ])

# Add AI exports if available
if HAS_AI_SUPPORT:
    __all__.extend([
        "EnhancedVideoProcessor",
        "EnhancedVideoProcessingResult",
        "VideoContentAnalyzer",
        "ContentAnalysis",
        "SceneAnalysis",
    ])
