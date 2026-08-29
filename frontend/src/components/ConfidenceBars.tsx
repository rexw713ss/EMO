import { groupConfidenceScores } from '../services/visualStateGroups'
import { VISUAL_STATES } from '../services/visualStates'

interface ConfidenceBarsProps {
  scores: Record<string, number>
}

export function ConfidenceBars({ scores }: ConfidenceBarsProps) {
  const groups = groupConfidenceScores(scores)

  return (
    <div className="grouped-confidence-list">
      {groups.map((group) => {
        const config = VISUAL_STATES[group.key]
        return (
          <div className="grouped-confidence-group" key={group.key}>
            <div className="grouped-confidence-group-header">
              <span className="grouped-confidence-dot" style={{ background: config.color }} />
              <strong>{config.label}</strong>
              <span className="grouped-confidence-total">
                {Math.round(group.total * 100)}%
              </span>
            </div>
            <div className="confidence-track group-track">
              <div
                className="confidence-fill"
                style={{
                  width: `${Math.min(100, Math.max(0, group.total * 100))}%`,
                  background: config.color,
                }}
              />
            </div>
            <div className="grouped-confidence-members">
              {group.members.map((member) => (
                <div className="confidence-row" key={member.label}>
                  <span>{member.label}</span>
                  <div className="confidence-track">
                    <div
                      className="confidence-fill"
                      style={{ width: `${Math.min(100, Math.max(0, member.value * 100))}%` }}
                    />
                  </div>
                  <strong>{Math.round(member.value * 100)}%</strong>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
