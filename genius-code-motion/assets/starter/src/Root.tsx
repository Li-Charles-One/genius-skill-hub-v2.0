import {Composition} from 'remotion';
import {Video} from './Overlay';
import {DURATION, FPS, HEIGHT, WIDTH} from './timeline';

export const Root: React.FC = () => (
  <Composition id="Main" component={Video} durationInFrames={DURATION} fps={FPS} width={WIDTH} height={HEIGHT} />
);
