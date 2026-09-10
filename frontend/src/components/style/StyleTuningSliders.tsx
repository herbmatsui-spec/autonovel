import React, { useState } from "react";

export interface StyleTuningParams {
  kemeritsu: number;
  bodyStop: number;
  metaphor: number;
}

interface StyleTuningSlidersProps {
  onChange: (params: StyleTuningParams) => void;
}

export const StyleTuningSliders: React.FC<StyleTuningSlidersProps> = ({ onChange }) => {
  const [kemeritsu, setKemeritsu] = useState(3);
  const [bodyStop, setBodyStop] = useState(50);
  const [metaphor, setMetaphor] = useState(50);

  const handleKemeritsuChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    setKemeritsu(value);
    onChange({ kemeritsu: value, bodyStop, metaphor });
  };

  const handleBodyStopChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    setBodyStop(value);
    onChange({ kemeritsu, bodyStop: value, metaphor });
  };

  const handleMetaphorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    setMetaphor(value);
    onChange({ kemeritsu, bodyStop, metaphor: value });
  };

  return (
    <div className="style-tuning-sliders">
      <div className="slider-group">
        <label>ケレン味（過剰演出）強度</label>
        <div className="slider-container">
          <input
            type="range"
            min="1"
            max="5"
            value={kemeritsu}
            onChange={handleKemeritsuChange}
            className="slider"
          />
          <div className="slider-labels">
            <span>1: 抑制・淡々</span>
            <span>3: 王道Web小説調</span>
            <span>5: 劇的・過剰ケレン味</span>
          </div>
          <div className="slider-value">{kemeritsu}</div>
        </div>
      </div>
      <div className="slider-group">
        <label>文末リズム（だ・である vs 体言止め）</label>
        <div className="slider-container">
          <input
            type="range"
            min="0"
            max="100"
            value={bodyStop}
            onChange={handleBodyStopChange}
            className="slider"
          />
          <div className="slider-labels">
            <span>0: だ・である中心</span>
            <span>50: バランス</span>
            <span>100: 体言止め・短文連打</span>
          </div>
          <div className="slider-value">{bodyStop}%</div>
        </div>
      </div>
      <div className="slider-group">
        <label>比喩・五感描写の濃厚さ</label>
        <div className="slider-container">
          <input
            type="range"
            min="0"
            max="100"
            value={metaphor}
            onChange={handleMetaphorChange}
            className="slider"
          />
          <div className="slider-labels">
            <span>0: ほとんどなし</span>
            <span>50: 普通</span>
            <span>100: 非常に濃厚</span>
          </div>
          <div className="slider-value">{metaphor}</div>
        </div>
      </div>
    </div>
  );
};