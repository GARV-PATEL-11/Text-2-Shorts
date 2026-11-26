// You, in a pop-up from the header: the name Faraday calls you (kept on this machine), the Claude account Claude Code
// is signed in to, how many runs this machine holds and what their console turns have cost; Sign Out lives here.
import { useEffect, useState } from "react";
import { useSession } from "../../app/session";
import { useAction } from "../../hooks/useAction";
import { send } from "../../services/http";
import type { Profile } from "../../types/api";
import { Modal } from "../feedback/Overlay";
import { Notice } from "../feedback/Notice";
import { Button } from "../ui/Button";
import { Field } from "../ui/fields";
import { titleCase } from "../ui/text";

export function ProfileDialog({ profile, isOpen, onOpenChange, onSaved }: {
  profile: Profile | null; isOpen: boolean; onOpenChange: (open: boolean) => void; onSaved: () => void;
}) {
  const { account, signOut } = useSession();
  const [name, setName] = useState("");
  const action = useAction();
  useEffect(() => { if (isOpen) setName(profile?.name ?? ""); }, [isOpen, profile]);
  const save = () => action.run("Saving…", async () => {
    await send<Profile>("/api/profile", { name: name.trim() }, "PUT");
    onSaved();
    return "Saved";
  });
  const leave = () => action.run("Signing Out…", async () => {
    const problem = await signOut();
    if (problem) throw new Error(problem);
  });
  const who = profile?.account ?? account;
  return (
    <Modal isOpen={isOpen} onOpenChange={onOpenChange} title="Your Profile" description={who?.email}
      footer={<>
        <Button variant="secondary" onPress={leave} isDisabled={action.busy}>Sign Out</Button>
        <Button onPress={save} isDisabled={action.busy || name.trim() === (profile?.name ?? "")}>Save</Button>
      </>}>
      <div className="stack">
        <Field label="Your Name" value={name} onChange={setName} maxLength={80} placeholder={who?.email.split("@")[0]}
          hint="How Faraday Shows You; Kept on This Computer" />
        <dl className="facts">
          <div><dt>Organization</dt><dd>{who?.organization || "—"}</dd></div>
          <div><dt>Plan</dt><dd>{who?.plan ? titleCase(who.plan) : "—"}</dd></div>
          <div><dt>Signed In With</dt><dd>{who?.method || "—"}</dd></div>
          <div><dt>Runs Here</dt><dd>{profile ? profile.runs : "—"}</dd></div>
          <div><dt>Net Spend</dt><dd>{profile ? `$${profile.spend_usd.toFixed(2)}` : "—"}</dd></div>
        </dl>
        <p className="note">Net Spend Adds Up the Cost Claude Code Reports for Every Console Turn; on a Subscription It Is What the Same Use Would Cost at API Prices</p>
        <Notice note={action.note} />
      </div>
    </Modal>
  );
}
