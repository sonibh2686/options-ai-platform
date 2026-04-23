type Props = {
  trade: any | null;
};

export default function TradeDetail({ trade }: Props) {
  if (!trade) return null;

  return (
    <div className="panel">
      <h3>
        {trade.ticker} {trade.strike} {trade.option_type.toUpperCase()} {trade.expiry}
      </h3>

      <div className="grid-detail">
        <div><b>Category</b><div>{trade.category}</div></div>
        <div><b>Recommendation</b><div>{trade.recommendation}</div></div>
        <div><b>Total Score</b><div>{trade.total_score}</div></div>
        <div><b>Mid Price</b><div>{trade.mid_price}</div></div>

        <div><b>Bid</b><div>{trade.bid}</div></div>
        <div><b>Ask</b><div>{trade.ask}</div></div>
        <div><b>IV</b><div>{(trade.implied_volatility * 100).toFixed(2)}%</div></div>
        <div><b>POP</b><div>{(trade.pop * 100).toFixed(1)}%</div></div>

        <div><b>Delta</b><div>{trade.delta}</div></div>
        <div><b>Gamma</b><div>{trade.gamma}</div></div>
        <div><b>Theta</b><div>{trade.theta}</div></div>
        <div><b>Vega</b><div>{trade.vega}</div></div>

        <div><b>Liquidity Score</b><div>{trade.liquidity_score}</div></div>
        <div><b>Greeks Score</b><div>{trade.greeks_score}</div></div>
        <div><b>IV Score</b><div>{trade.iv_score}</div></div>
        <div><b>OI Score</b><div>{trade.oi_score}</div></div>

        <div><b>Selected Strike OI</b><div>{trade.selected_strike_oi}</div></div>
        <div><b>Volume</b><div>{trade.volume}</div></div>
        <div><b>Open Interest</b><div>{trade.open_interest}</div></div>
        <div><b>Stock Score</b><div>{trade.stock_score}</div></div>
      </div>

      <div style={{ marginTop: 20 }}>
        <h4>Nearby Strike OI</h4>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Strike</th>
                <th>Call OI</th>
                <th>Put OI</th>
                <th>Call Vol</th>
                <th>Put Vol</th>
              </tr>
            </thead>
            <tbody>
              {(trade.nearby_oi_levels || []).map((row: any, idx: number) => (
                <tr key={idx}>
                  <td>{row.strike}</td>
                  <td>{row.call_oi}</td>
                  <td>{row.put_oi}</td>
                  <td>{row.call_volume}</td>
                  <td>{row.put_volume}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="detail-columns">
        <div>
          <h4>Reasons</h4>
          <ul>
            {trade.reasons?.map((r: string, i: number) => <li key={i}>{r}</li>)}
          </ul>
        </div>
        <div>
          <h4>Warnings</h4>
          <ul>
            {trade.warnings?.map((w: string, i: number) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
}