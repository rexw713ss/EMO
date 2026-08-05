import { useState, useEffect } from 'react';
import { EMOTION_CONFIGS } from '../constants/emotionConfig';

export function useEmotion(initialEmotion = 'UNKNOWN') {
  const [currentEmotion, setCurrentEmotion] = useState(initialEmotion);

  // 1. 手動切換情緒
  const changeEmotion = (emotionKey) => {
    if (EMOTION_CONFIGS[emotionKey]) {
      setCurrentEmotion(emotionKey);
    } else {
      setCurrentEmotion('UNKNOWN');
    }
  };

  // 2. 定期向後端（FastAPI）讀取最新的感應結果 (Polling 輪詢)
  useEffect(() => {
    const fetchBackendEmotion = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/emotion/current');
        if (!response.ok) return;
        
        const data = await response.json();
        // 假設後端傳回的格式為 { emotion: "CALM" }
        if (data?.emotion && EMOTION_CONFIGS[data.emotion]) {
          setCurrentEmotion(data.emotion);
        }
      } catch (err) {
        // 後端沒開或斷線時不報錯，繼續維持當前狀態
        console.warn('無法連線至後端感應器');
      }
    };

    // 每 3 秒向後端詢問一次感應結果
    const interval = setInterval(fetchBackendEmotion, 3000);
    return () => clearInterval(interval);
  }, []);

  return {
    currentEmotion,
    emotionData: EMOTION_CONFIGS[currentEmotion] || EMOTION_CONFIGS.UNKNOWN,
    changeEmotion
  };
}

export default useEmotion;