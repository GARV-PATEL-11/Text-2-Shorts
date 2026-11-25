// Buttons: primary (white), secondary (outlined), tertiary (quiet), in two heights (32, 40); a LinkButton for navigation.
import type { ReactNode } from "react";
import { Button as AriaButton, Link } from "react-aria-components";

type Variant = "primary" | "secondary" | "tertiary";
type Size = "sm" | "md";

const classes = (variant: Variant, size: Size, iconOnly: boolean) =>
  `button button--${variant} button--${size}${iconOnly ? " button--icon" : ""}`;

export function Button({ variant = "primary", size = "md", icon, children, onPress, isDisabled, type = "button", label, describedBy, expanded }: {
  variant?: Variant; size?: Size; icon?: ReactNode; children?: ReactNode; onPress?: () => void; isDisabled?: boolean;
  type?: "button" | "submit"; label?: string; describedBy?: string; expanded?: boolean;
}) {
  return (
    <AriaButton className={classes(variant, size, !children)} onPress={onPress} isDisabled={isDisabled} type={type}
      aria-label={label} aria-describedby={describedBy} aria-expanded={expanded}>
      {icon}
      {children}
    </AriaButton>
  );
}

export function LinkButton({ href, variant = "primary", size = "md", icon, children }: {
  href: string; variant?: Variant; size?: Size; icon?: ReactNode; children: ReactNode;
}) {
  return <Link href={href} className={classes(variant, size, false)}>{icon}{children}</Link>;
}
