import type { VisualStateKey } from '../types/emotion'

export const VISUAL_STATES: Record<
  VisualStateKey,
  {
    label: string
    description: string
    background: string
    color: string
    glow: string
    pulseSeconds: number
    breatheMin: number
    breatheMax: number
  }
> = {
  calm: {
    label: '平靜',
    description: '目前訊號較穩定、低喚起；保持自然呼吸即可。',
    background:
      'radial-gradient(52% 46% at 50% 40%, rgba(54, 197, 216, 0.20), transparent 70%),' +
      'radial-gradient(38% 30% at 78% 14%, rgba(120, 220, 232, 0.07), transparent 60%),' +
      'linear-gradient(165deg, #050f1c 0%, #0d2c46 42%, #17587c 72%, #0a1f30 100%)',
    color: '#78dce8',
    glow: '#36c5d8',
    pulseSeconds: 4.4,
    breatheMin: 0.93,
    breatheMax: 1.07,
  },
  pleasant: {
    label: '愉悅',
    description: '模型的 happy 信心度較高，呈現較明亮、開放的表情特徵。',
    background:
      'radial-gradient(52% 46% at 50% 40%, rgba(255, 191, 105, 0.20), transparent 70%),' +
      'radial-gradient(38% 30% at 76% 16%, rgba(255, 226, 154, 0.08), transparent 60%),' +
      'linear-gradient(165deg, #241019 0%, #5c2c22 42%, #a3572f 72%, #2f1721 100%)',
    color: '#ffe29a',
    glow: '#ffbf69',
    pulseSeconds: 2,
    breatheMin: 0.9,
    breatheMax: 1.1,
  },
  alert: {
    label: '緊張',
    description: 'anger、fear 或 surprise 的整體信號較高；這不代表心理診斷。',
    background:
      'radial-gradient(52% 46% at 50% 40%, rgba(255, 77, 95, 0.22), transparent 70%),' +
      'radial-gradient(38% 30% at 76% 16%, rgba(255, 139, 118, 0.08), transparent 60%),' +
      'linear-gradient(165deg, #22071d 0%, #641b30 42%, #a3392f 72%, #2b0b24 100%)',
    color: '#ff8b76',
    glow: '#ff4d5f',
    pulseSeconds: 0.85,
    breatheMin: 0.96,
    breatheMax: 1.05,
  },
  low: {
    label: '低落',
    description: '目前訊號偏低活性或負向，結果可能受光線與角度影響。',
    background:
      'radial-gradient(52% 46% at 50% 40%, rgba(141, 107, 232, 0.20), transparent 70%),' +
      'radial-gradient(38% 30% at 78% 14%, rgba(189, 162, 255, 0.07), transparent 60%),' +
      'linear-gradient(165deg, #0a0817 0%, #251b40 42%, #402a5e 72%, #150f28 100%)',
    color: '#bda2ff',
    glow: '#8d6be8',
    pulseSeconds: 7,
    breatheMin: 0.95,
    breatheMax: 1.03,
  },
  unknown: {
    label: '未知',
    description: '尚未取得可靠的人臉訊號，請面向鏡頭並保持光線充足。',
    background:
      'radial-gradient(52% 46% at 50% 40%, rgba(135, 147, 161, 0.16), transparent 70%),' +
      'radial-gradient(38% 30% at 78% 14%, rgba(185, 194, 204, 0.06), transparent 60%),' +
      'linear-gradient(165deg, #0b0e13 0%, #1c232c 42%, #313b46 72%, #171c22 100%)',
    color: '#b9c2cc',
    glow: '#8793a1',
    pulseSeconds: 5,
    breatheMin: 0.94,
    breatheMax: 1.06,
  },
}
