import { useState } from 'react';
import { EMOTION_CONFIGS } from '../constants/emotionConfig';

export function useEmotion(initialEmotion = 'UNKNOWN') {
  const [currentEmotion, setCurrentEmotion] = useState(initialEmotion);

  // 提供安全的切換情緒方法
  const changeEmotion = (emotionKey) => {
    if (EMOTION_CONFIGS[emotionKey]) {
      setCurrentEmotion(emotionKey);
    } else {
      setCurrentEmotion('UNKNOWN');
    }
  };

  return {
    currentEmotion,
    emotionData: EMOTION_CONFIGS[currentEmotion] || EMOTION_CONFIGS.UNKNOWN,
    changeEmotion
  };
}
export default useEmotion;