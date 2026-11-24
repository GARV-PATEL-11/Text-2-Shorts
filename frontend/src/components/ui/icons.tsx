// Icons: Untitled UI Icons (MIT, @untitledui/icons), 24×24 line icons in the text colour (black or white only), named
// here by what they mean in Faraday. Media controls are filled, as players draw them.
import type { ComponentType, SVGProps } from "react";
import {
  AlertCircle, ArrowLeft as UArrowLeft, ArrowRight as UArrowRight, Check as UCheck, ChevronDown as UChevronDown,
  ChevronLeft as UChevronLeft, ChevronRight as UChevronRight, Clapperboard as UClapperboard,
  ClipboardCheck as UClipboardCheck, Clock as UClock, Dataflow03, Dice3, Edit05, Film01, Home02, Image01, LayoutGrid01,
  Lock01, Maximize01, MessageChatCircle, MessageQuestionCircle, Minimize01, Palette as UPalette, PlayCircle,
  Plus as UPlus, SearchLg, Shuffle01, SlashCircle01, Stars02, SwitchVertical01, Terminal as UTerminal, Users01,
  VolumeMax, WifiOff, XClose,
} from "@untitledui/icons";

const SIZE = 20;
type Props = SVGProps<SVGSVGElement>;
const sized = (Glyph: ComponentType<Props & { size?: number }>) => (props: Props) => <Glyph size={SIZE} focusable="false" {...props} />;

// navigation and actions
export const HomeIcon = sized(Home02);
export const ChevronRight = sized(UChevronRight);
export const ChevronLeft = sized(UChevronLeft);
export const ChevronDown = sized(UChevronDown);
export const ArrowLeft = sized(UArrowLeft);
export const ArrowRight = sized(UArrowRight);
export const Plus = sized(UPlus);
export const Close = sized(XClose);
export const Check = sized(UCheck);
export const Search = sized(SearchLg);
export const Swap = sized(SwitchVertical01);
export const Expand = sized(Maximize01);
export const Shrink = sized(Minimize01);
export const Terminal = sized(UTerminal);
export const Message = sized(MessageChatCircle);
export const Volume = sized(VolumeMax);
export const Render = sized(Stars02);
export const Dice = sized(Dice3);
export const Picture = sized(Image01);

// the stages of a run, and the steps to start one
export const Palette = sized(UPalette);
export const Requirements = sized(UClipboardCheck);
export const Outline = sized(Dataflow03);
export const Script = sized(Edit05);
export const Storyboard = sized(LayoutGrid01);
export const Clapperboard = sized(UClapperboard);
export const FinalVideo = sized(PlayCircle);
export const Shuffle = sized(Shuffle01);
export const Question = sized(MessageQuestionCircle);
export const Audience = sized(Users01);

// states
export const Film = sized(Film01);
export const Clock = sized(UClock);
export const Lock = sized(Lock01);
export const Slash = sized(SlashCircle01);
export const Wifi = sized(WifiOff);
export const Alert = sized(AlertCircle);

// media controls (filled)
export const Play = () => <svg viewBox="0 0 24 24" width={SIZE} height={SIZE} fill="currentColor" aria-hidden="true" focusable="false"><path d="M7 4.9v14.2a1 1 0 0 0 1.5.86l11.6-7.1a1 1 0 0 0 0-1.72L8.5 4.04A1 1 0 0 0 7 4.9z" /></svg>;
export const Pause = () => <svg viewBox="0 0 24 24" width={SIZE} height={SIZE} fill="currentColor" aria-hidden="true" focusable="false"><rect x="6" y="4.5" width="4" height="15" rx="1" /><rect x="14" y="4.5" width="4" height="15" rx="1" /></svg>;
