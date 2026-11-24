// Breadcrumbs: home, then each level; the last one is where you are.
import { Breadcrumb, Breadcrumbs as AriaBreadcrumbs, Link } from "react-aria-components";
import { ChevronRight, HomeIcon } from "../ui/icons";

export function Breadcrumbs({ trail }: { trail: { label: string; href?: string }[] }) {
  return (
    <AriaBreadcrumbs className="breadcrumbs">
      <Breadcrumb className="breadcrumbs__item">
        <Link href="#/" className="breadcrumbs__link" aria-label="Home"><HomeIcon /></Link>
        <ChevronRight />
      </Breadcrumb>
      {trail.map((crumb, index) => (
        <Breadcrumb key={`${crumb.label}-${index}`} className="breadcrumbs__item">
          <Link href={index < trail.length - 1 ? crumb.href : undefined} className="breadcrumbs__link">{crumb.label}</Link>
          {index < trail.length - 1 ? <ChevronRight /> : null}
        </Breadcrumb>
      ))}
    </AriaBreadcrumbs>
  );
}
