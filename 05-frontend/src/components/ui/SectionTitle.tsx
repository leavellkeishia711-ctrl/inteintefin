import React from 'react';

interface SectionTitleProps {
  children: React.ReactNode;
  action?: React.ReactNode;
}

export const SectionTitle: React.FC<SectionTitleProps> = ({ children, action }) => (
  <div className="flex items-center justify-between mb-4">
    <h3 className="font-semibold text-gray-900">{children}</h3>
    {action}
  </div>
);
