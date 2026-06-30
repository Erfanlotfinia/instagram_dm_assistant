import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import type { TrustTestPack } from '../../types/sprint6Trust';
import type { BadgeTone } from '../ui';

const severityTone: Record<TrustTestPack['testCases'][number]['severity'], BadgeTone> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'neutral',
};

export interface TrustTestPackCardProps {
  pack: TrustTestPack;
  onRun: () => void;
  running?: boolean;
  hasScenarioPack?: boolean;
  disabled?: boolean;
}

export function TrustTestPackCard({
  pack,
  onRun,
  running,
  hasScenarioPack,
  disabled,
}: TrustTestPackCardProps) {
  const severityCounts = pack.testCases.reduce<Record<string, number>>((acc, tc) => {
    acc[tc.severity] = (acc[tc.severity] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card className="flex flex-col">
      <CardHeader
        title={pack.name}
        description={pack.description}
        actions={<Badge tone="neutral">{pack.testCases.length} tests</Badge>}
      />
      <CardBody className="flex flex-1 flex-col gap-3">
        <div className="flex flex-wrap gap-1.5">
          {(['critical', 'high', 'medium', 'low'] as const).map((sev) =>
            severityCounts[sev] ? (
              <Badge key={sev} tone={severityTone[sev]}>
                {sev}: {severityCounts[sev]}
              </Badge>
            ) : null,
          )}
        </div>
        <p className="text-xs text-muted">
          Category: <span className="text-fg">{pack.category}</span>
        </p>
        {hasScenarioPack ? (
          <p className="text-xs text-success">Scenario pack linked to regression.</p>
        ) : (
          <p className="text-xs text-muted">
            Connect this pack to Scenario Regression to run live simulations.
          </p>
        )}
        <div className="mt-auto pt-2">
          <Button
            type="button"
            size="sm"
            disabled={disabled || running}
            onClick={onRun}
          >
            {running ? 'Running…' : hasScenarioPack ? 'Run pack' : 'Create & run pack'}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
