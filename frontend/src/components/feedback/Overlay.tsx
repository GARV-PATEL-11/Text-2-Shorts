// Overlays: a modal dialog (fades in and out) and a side drawer (slides in from the right — the one slide in the
// app). React Aria keeps them mounted until their exit animation ends; focus is trapped and returned on close.
import type { ReactNode } from "react";
import { Dialog, Heading, Modal as AriaModal, ModalOverlay } from "react-aria-components";
import { Button } from "../ui/Button";
import { Close } from "../ui/icons";

export function Modal({ isOpen, onOpenChange, title, description, icon, children, footer, size = "md" }: {
  isOpen: boolean; onOpenChange: (open: boolean) => void; title: string; description?: ReactNode; icon?: ReactNode;
  children?: ReactNode; footer?: ReactNode; size?: "md" | "lg" | "xl";
}) {
  return (
    <ModalOverlay className="overlay" isOpen={isOpen} onOpenChange={onOpenChange} isDismissable>
      <AriaModal className={`modal modal--${size}`}>
        <Dialog className="modal__dialog">
          {({ close }) => (
            <>
              <div className="modal__head">
                {icon ? <span className="featured-icon">{icon}</span> : null}
                <div>
                  <Heading slot="title" className="modal__title">{title}</Heading>
                  {description ? <p className="modal__description">{description}</p> : null}
                </div>
                <Button variant="tertiary" size="sm" icon={<Close />} onPress={close} label="Close" />
              </div>
              {children ? <div className="modal__body">{children}</div> : null}
              {footer ? <div className="modal__foot">{footer}</div> : null}
            </>
          )}
        </Dialog>
      </AriaModal>
    </ModalOverlay>
  );
}

export function Drawer({ isOpen, onOpenChange, title, description, children }: {
  isOpen: boolean; onOpenChange: (open: boolean) => void; title: string; description?: ReactNode; children: ReactNode;
}) {
  return (
    <ModalOverlay className="overlay overlay--drawer" isOpen={isOpen} onOpenChange={onOpenChange} isDismissable>
      <AriaModal className="drawer">
        <Dialog className="drawer__dialog">
          {({ close }) => (
            <>
              <div className="drawer__head">
                <div>
                  <Heading slot="title" className="modal__title">{title}</Heading>
                  {description ? <p className="modal__description">{description}</p> : null}
                </div>
                <Button variant="tertiary" size="sm" icon={<Close />} onPress={close} label="Close" />
              </div>
              <div className="drawer__body">{children}</div>
            </>
          )}
        </Dialog>
      </AriaModal>
    </ModalOverlay>
  );
}
