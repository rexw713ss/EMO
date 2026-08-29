import { useEffect, useState } from 'react'
import { fetchModelEvaluation } from '../services/modelEvalApi'
import type { ModelEvaluationData } from '../types/emotion'

const STATUS_LABELS: Record<string, string> = {
  in_use: '使用中',
  needs_license: '需申請授權',
  candidate: '候選',
}

export function ModelEvaluation() {
  const [data, setData] = useState<ModelEvaluationData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchModelEvaluation()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((cause) => {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : '無法載入模型評估資料')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return <p className="inline-error">{error}</p>
  }

  if (!data) {
    return <p className="empty-state">載入中…</p>
  }

  return (
    <div className="model-eval-body">
      {data.is_estimate && (
        <div className="threshold-alert-banner estimate-banner">
          <strong>示意數據，待實測填入</strong>
          <span>{data.estimate_note}</span>
        </div>
      )}

      <section className="metric-grid">
        <article className="metric-card primary-metric">
          <span>準確度</span>
          <strong>{data.accuracy_pct.toFixed(2)}%</strong>
          <small>自訓模型 · {data.sample_count} 張測試集</small>
        </article>
        <article className="metric-card">
          <span>+TTA 準確度</span>
          <strong>{data.tta_accuracy_pct.toFixed(2)}%</strong>
          <small>測試時擴增</small>
        </article>
        <article className="metric-card">
          <span>目前樣本數</span>
          <strong>{data.sample_count}</strong>
          <small>目標 {data.target_sample_count} 張</small>
        </article>
        <article className="metric-card">
          <span>信賴區間</span>
          <strong>±{data.confidence_interval_pct}%</strong>
          <small>樣本數偏小，區間偏寬</small>
        </article>
      </section>

      <section className="dashboard-grid model-eval-grid">
        <article className="panel confusion-matrix-panel">
          <div className="panel-title">
            <div>
              <span>CONFUSION MATRIX</span>
              <h2>8×8 混淆矩陣</h2>
            </div>
            <small>列：實際 · 欄：預測</small>
          </div>
          <div className="confusion-matrix-scroll">
            <table className="confusion-matrix-table">
              <thead>
                <tr>
                  <th />
                  {data.class_names.map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.confusion_matrix.map((row, rowIndex) => (
                  <tr key={data.class_names[rowIndex]}>
                    <th>{data.class_names[rowIndex]}</th>
                    {row.map((value, colIndex) => (
                      <td
                        key={colIndex}
                        className={rowIndex === colIndex ? 'diagonal' : ''}
                      >
                        {value}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel per-class-panel">
          <div className="panel-title">
            <div>
              <span>PER-CLASS</span>
              <h2>各類 P / R / F1</h2>
            </div>
          </div>
          <table className="per-class-table">
            <thead>
              <tr>
                <th>類別</th>
                <th>P</th>
                <th>R</th>
                <th>F1</th>
                <th>N</th>
              </tr>
            </thead>
            <tbody>
              {data.per_class_metrics.map((metric) => (
                <tr key={metric.label}>
                  <td>{metric.label}</td>
                  <td>{metric.precision.toFixed(2)}</td>
                  <td>{metric.recall.toFixed(2)}</td>
                  <td>{metric.f1.toFixed(2)}</td>
                  <td>{metric.support}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="panel-title subgroup-title">
            <div>
              <span>SUBGROUPS</span>
              <h2>分組表現</h2>
            </div>
          </div>
          <ul className="subgroup-list">
            {data.subgroup_metrics.map((subgroup) => (
              <li key={subgroup.condition}>
                <span>{subgroup.condition}</span>
                <strong>{subgroup.accuracy.toFixed(1)}%</strong>
                <small>n={subgroup.sample_count}</small>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="panel dataset-candidates-panel">
        <div className="panel-title">
          <div>
            <span>DATASETS</span>
            <h2>候選資料集</h2>
          </div>
        </div>
        <table className="dataset-candidates-table">
          <thead>
            <tr>
              <th>資料集</th>
              <th>類別數</th>
              <th>含 contempt</th>
              <th>狀態</th>
              <th>備註</th>
            </tr>
          </thead>
          <tbody>
            {data.dataset_candidates.map((candidate) => (
              <tr key={candidate.name}>
                <td>{candidate.name}</td>
                <td>{candidate.class_count}</td>
                <td>{candidate.has_contempt ? '有' : '無'}</td>
                <td>
                  <span className={`dataset-status status-${candidate.status}`}>
                    {STATUS_LABELS[candidate.status] ?? candidate.status}
                  </span>
                </td>
                <td>{candidate.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel next-steps-panel">
        <div className="panel-title">
          <div>
            <span>NEXT STEPS</span>
            <h2>下一步</h2>
          </div>
        </div>
        <ol className="next-steps-list">
          {data.next_steps.map((step, index) => (
            <li key={index}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
