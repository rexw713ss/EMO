import React from 'react';
import EmotionVisualDisplay from './components/EmotionVisualDisplay';
import EmotionControlPanel from './components/EmotionControlPanel';
import { useEmotion } from './hooks/useEmotion';

export default function App() {
  // 使用新的 Custom Hook 取得當前情緒 Key、情緒詳細設定與切換函式
  const { currentEmotion, emotionData, changeEmotion } = useEmotion('UNKNOWN');

  return (
    <EmotionVisualDisplay emotionData={emotionData}>
      <EmotionControlPanel
        currentEmotion={currentEmotion}
        onSelectEmotion={changeEmotion}
      />
    </EmotionVisualDisplay>
  );
}