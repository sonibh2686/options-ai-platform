type Props = {
  title: string;
  value: string | number;
  subtitle?: string;
};

export default function ScoreCard({ title, value, subtitle }: Props) {
  return (
    <div className="card">
      <div className="card-label">{title}</div>
      <div className="card-value">{value}</div>
      {subtitle ? <div className="card-sub">{subtitle}</div> : null}
    </div>
  );
}