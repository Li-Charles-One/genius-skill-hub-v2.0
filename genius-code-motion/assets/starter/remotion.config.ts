import {Config} from '@remotion/cli/config';

// macOS 上 Three.js 需要 angle 后端才能出图
Config.setChromiumOpenGlRenderer('angle');
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
