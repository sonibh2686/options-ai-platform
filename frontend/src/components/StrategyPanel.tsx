type Props = {
  strategy: any | null;
};

export default function StrategyPanel({ strategy }: Props) {
  if (!strategy) return null;

  return (
    <div className="panel">
      <h2>Best Strategy Recommendation</h2>

      <div className="grid-detail">
        <div>
          <b>Strategy</b>
          <div>{strategy.strategy_name}</div>
        </div>
        <div>
          <b>Bias</b>
          <div>{strategy.strategy_bias}</div>
        </div>
        <div>
          <b>Strategy Score</b>
          <div>{strategy.strategy_score}</div>
        </div>
        <div>
          <b>Expiry</b>
          <div>{strategy.legs?.[0]?.expiry || "-"}</div>
        </div>

        <div>
          <b>Estimated Debit</b>
          <div>{strategy.estimated_debit}</div>
        </div>
        <div>
          <b>Estimated Credit</b>
          <div>{strategy.estimated_credit}</div>
        </div>
        <div>
          <b>Max Profit</b>
          <div>{String(strategy.max_profit)}</div>
        </div>
        <div>
          <b>Max Loss</b>
          <div>{String(strategy.max_loss)}</div>
        </div>

        <div>
          <b>Breakeven Low</b>
          <div>{strategy.breakeven_low ?? "-"}</div>
        </div>
        <div>
          <b>Breakeven High</b>
          <div>{strategy.breakeven_high ?? "-"}</div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <b>Reason</b>
        <div style={{ marginTop: 6 }}>{strategy.strategy_reason}</div>
      </div>

      <div style={{ marginTop: 20 }}>
        <h3>Strategy Legs</h3>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Type</th>
                <th>Strike</th>
                <th>Expiry</th>
                <th>Premium</th>
              </tr>
            </thead>
            <tbody>
              {(strategy.legs || []).map((leg: any, idx: number) => (
                <tr key={idx}>
                  <td>{leg.action}</td>
                  <td>{leg.type}</td>
                  <td>{leg.strike}</td>
                  <td>{leg.expiry}</td>
                  <td>{leg.premium}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}