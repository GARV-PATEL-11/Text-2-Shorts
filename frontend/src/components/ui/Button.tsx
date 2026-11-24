// Buttons: primary (white), secondary (outlined), tertiary (quiet), in three heights; a LinkButton for navigation.
import type { ReactNode } from "react";
import { Button as AriaButton, Link } from "react-aria-components";

type Variant = "primary" | "secondary" | "tertiary";
type Size = "sm" | "md" | "lg";

const classes = (variant: Variant, size: Size, iconOnly: boolean) =>
  `button button--${variant} button--${size}${iconOnly ? " button--icon" : ""}`;

export function Button({ variant = "primary", size = "md", icon, children, onPress, isDisabled, type = "button", label, describedBy }: {
  variant?: Variant; size?: Size; icon?: ReactNode; children?: ReactNode; onPress?: () => void; isDisabled?: boolean;
  type?: "button" | "submit"; label?: string; describedBy?: string;
}) {
  return (
    <AriaButton className={classes(variant, size, !children)} onPress={onPress} isDisabled={isDisabled} type={type}
      aria-label={label} aria-describedby={describedBy}>
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
