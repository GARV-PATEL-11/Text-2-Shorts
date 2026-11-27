// Tabs: an underlined row of sub-stages; a count badge flags what needs you.
import type { ReactNode } from "react";
import { Tab, TabList, TabPanel, Tabs as AriaTabs } from "react-aria-components";

export interface TabSpec { id: string; label: string; count?: number; content: ReactNode }

export function Tabs({ label, selected, onChange, tabs, toolbar }: {
  label: string; selected: string; onChange: (id: string) => void; tabs: TabSpec[]; toolbar?: ReactNode;
}) {
  return (
    <AriaTabs className="tabs" selectedKey={selected} onSelectionChange={(key) => onChange(String(key))}>
      <div className="tabs__bar">
        <TabList className="tabs__list" aria-label={label}>
          {tabs.map((tab) => (
            <Tab key={tab.id} id={tab.id} className="tabs__tab">
              {tab.label}
              {tab.count ? <span className="badge badge--count" aria-label={tab.id === "checkpoint" || tab.id === "approval" ? `${tab.count} Waiting for You` : String(tab.count)}>{tab.count}</span> : null}
            </Tab>
          ))}
        </TabList>
        {toolbar ? <div className="tabs__toolbar">{toolbar}</div> : null}
      </div>
      {tabs.map((tab) => <TabPanel key={tab.id} id={tab.id} className="tabs__panel">{tab.content}</TabPanel>)}
    </AriaTabs>
  );
}
