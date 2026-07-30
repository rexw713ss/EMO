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
  }
> = {
  calm: {
    label: '平靜',
    description: '目前訊號較穩定、低喚起；保持自然呼吸即可。',
    background: 'linear-gradient(145deg, #07172c 0%, #123e61 52%, #1b6b83 100%)',
    color: '#78dce8',
    glow: '#36c5d8',
    pulseSeconds: 4,
  },
  pleasant: {
    label: '愉悅',
    description: '模型的 happy 信心度較高，呈現較明亮、開放的表情特徵。',
    background: 'linear-gradient(145deg, #2f1721 0%, #a34d38 52%, #efaa57 100%)',
    color: '#ffe29a',
    glow: '#ffbf69',
    pulseSeconds: 2,
  },
  alert: {
    label: '緊張',
    description: 'anger、fear 或 surprise 的整體信號較高；這不代表心理診斷。',
    background: 'linear-gradient(145deg, #2b0b24 0%, #8d243a 50%, #ef643e 100%)',
    color: '#ff8b76',
    glow: '#ff4d5f',
    pulseSeconds: 0.9,
  },
  low: {
    label: '低落',
    description: '目前訊號偏低活性或負向，結果可能受光線與角度影響。',
    background: 'linear-gradient(145deg, #100d22 0%, #30204f 55%, #553a73 100%)',
    color: '#bda2ff',
    glow: '#8d6be8',
    pulseSeconds: 6,
  },
  unknown: {
    label: '未知',
    description: '尚未取得可靠的人臉訊號，請面向鏡頭並保持光線充足。',
    background: 'linear-gradient(145deg, #10151d 0%, #252e39 55%, #3d4854 100%)',
    color: '#b9c2cc',
    glow: '#8793a1',
    pulseSeconds: 5,
  },
}
