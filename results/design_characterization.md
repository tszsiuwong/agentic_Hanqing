# Design Characterization

| 指标 | [GCD](results/gcd/gcd_report.md) | [JPEG](results/jpeg/jpeg_report.md) |
|------|------|------|
| Instance | 301 | 39,866 |
| Cell 类型 | 23 | 47 |
| Port | 56 | 53 |
| Net | 376 | 48,752 |
| Rent p | 1.366 | 1.215 |
| C/S 比 | 7.9:1 | 8.0:1 |
| Degree μ | 3.6 | 3.6 |
| Fanout μ | 3.0 | 2.9 |

## 趋势

- **规模**：JPEG 是 GCD 的 132 倍，但 IO 口基本相同
- **Rent p**：JPEG 更低（1.215 vs 1.366），大规模下连线增长更可控
- **单元分布**：同为 Nangate45 库，Degree 均值一致（3.6）
- **组合/时序比**：两者接近，均为组合逻辑主导
