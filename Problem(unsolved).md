# 节拍器音量不稳定问题分析

## 现象

Web 版节拍器在高 BPM 或弱拍（低频 800Hz）时，各拍之间的音量不一致。

## 第一轮修复尝试

### 措施
1. `playClick` 接收显式 `time` 参数，避免依赖全局 `nextNoteTime`
2. `t = Math.max(time, audioCtx.currentTime)` 防止包络事件时间落在过去
3. `scheduleAheadTime` 从 0.1s 增加到 0.2s
4. `lookahead` 从 25ms 减少到 10ms
5. 添加时间漂移保护（落后 100ms 时自动重新同步）
6. UI 更新改用 `requestAnimationFrame`，避免 `setTimeout` 回调堆积
7. 预生成噪声 buffer，避免重复创建 `AudioBuffer` 的 GC 压力

### 未解决原因

以上修复仅解决了**调度抖动**导致的偶发包络变形问题，但未触及根本：

**Web Audio API `OscillatorNode` 的初始相位是随机的。**

每次调用 `playClick` 时，代码会新建两个 `OscillatorNode`（主频 + 泛音）。根据 Web Audio API 规范，振荡器启动时的初始相位不可控。这意味着：

- 主频振荡器（1200Hz 或 800Hz）和泛音振荡器（1.55 倍频）每次启动时的相对相位都不同
- 两个频率相近的正弦波叠加时，相位关系直接决定合成振幅
- 相长干涉时响度更大，相消干涉时响度更小
- 这种随机性在低频（800Hz）时感知更明显，因为波形周期更长，相位差异的影响更显著

而 metronome.py 中，`generate_click_pygame()` 在初始化阶段**只生成一次**波形数据，后续每次播放都是完全相同的 `pygame.mixer.Sound` 对象，不存在相位随机性问题。

## 根本解决方案

放弃实时 `OscillatorNode` 合成，改为**预生成 `AudioBuffer`**：

1. 在 `initAudio()` 或首次播放时，用 JavaScript 复现 `generate_click_pygame()` 的波形生成算法
2. 生成两个 `AudioBuffer`：`bufferHigh`（重拍，1200Hz）和 `bufferLow`（弱拍，800Hz）
3. 播放时使用 `AudioBufferSourceNode` 直接播放预先生成的 buffer
4. 这样每次播放的波形完全一致，彻底消除相位随机性

此方案在音色还原度和音量稳定性上都与 metronome.py 完全一致。
