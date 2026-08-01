import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface TrendTagProps {
  change: number;
  trend: 'up' | 'down' | 'neutral';
  invert?: boolean;
}

export const TrendTag: React.FC<TrendTagProps> = ({ change, trend, invert }) => {
  const isGood = invert ? trend === 'down' : trend === 'up';
  const isNeutral = change === 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${isNeutral ? 'text-gray-400' : isGood ? 'text-green-700' : 'text-red-700'}`}>
      {trend === 'up' && <ArrowUpRight size={12} />}
      {trend === 'down' && <ArrowDownRight size={12} />}
      {trend === 'neutral' && <Minus size={12} />}
      {Math.abs(change)}%
    </span>
  );
};
