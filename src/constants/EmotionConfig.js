export const EMOTION_CONFIGS = {
  CALM: {
    label: '平靜',
    bgColor: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
    elementColor: '#70a1ff',
    pulseDuration: '4s',
    description: '目前偵測到的情緒較為穩定;保持自然呼吸即可'
  },
  JOY: {
    label: '愉悅',
    bgColor: 'linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%)',
    elementColor: '#ffeaa7',
    pulseDuration: '2s',
    description: '模型happy信心度高，呈現較明亮 開放的表情'
  },
  ANXIOUS: {
    label: '緊張',
    bgColor: 'linear-gradient(135deg, #eb3b5a 0%, #fa8231 100%)',
    elementColor: '#ff4d4d',
    pulseDuration: '0.8s',
    description: 'anger fear 或 suprise 的整體信號較高'
  },
  DEPRESSED: {
    label: '低落',
    bgColor: 'linear-gradient(135deg, #2d1436 0%, #4b1248 100%)',
    elementColor: '#a55eea',
    pulseDuration: '6s',
    description: '目前訊號低活性或負面，結果可能受光線與角度影響'
  },
  UNKNOWN: {
    label: '未知',
    bgColor: 'linear-gradient(135deg, #3a3d40 0%, #181719 100%)',
    elementColor: '#a0a0a0',
    pulseDuration: '5s',
    description: '目前無法明確判定情緒'
  }
};

// ⚠️ 關鍵：一定要寫這行，元件才能自動取得包含 UNKNOWN 的按鈕陣列
export const EMOTION_KEYS = Object.keys(EMOTION_CONFIGS);