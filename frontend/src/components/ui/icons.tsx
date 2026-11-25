// The icon map: Untitled UI Icons (@untitledui/icons 0.0.23; free for personal and commercial use, the icons themselves
// not to be redistributed), 24×24 line icons in the text color, one meaning per glyph. Named here by what they mean in
// Faraday; docs/DESIGN_REFERENCE.md lists every mapping and the alternatives the council rejected. Media controls are
// filled, as players draw them.
import type { ComponentType, SVGProps } from "react";
import {
  AlertCircle, AlertTriangle,  ArrowLeft as UArrowLeft, ArrowRight as UArrowRight, Bell01, Calendar as UCalendar, 
  Check as UCheck, CheckCircle, ChevronDown as UChevronDown, ChevronLeft as UChevronLeft, ChevronRight as UChevronRight,
  Circle, Clapperboard as UClapperboard, ClipboardCheck, Clock as UClock, ClockStopwatch, Dataflow03, Dice3, Edit05, Eye,
  Film01, Home02, Image01, Inbox01, InfoCircle, LayoutGrid01, Loading02, Lock01, Maximize01, MessageChatCircle,
  MessagePlusCircle, Minimize01, MinusCircle, Moon01, Palette as UPalette, PlayCircle, Plus as UPlus, RefreshCw05, SearchLg, Shuffle01,
  SlashCircle01, Sun as USun, SwitchVertical01, Terminal as UTerminal, VolumeMax, WifiOff, XCircle, XClose,
} from "@untitledui/icons";

type Props = SVGProps<SVGSVGElement>;
const sized = (Glyph: ComponentType<Props & { size?: number }>) => (props: Props) => <Glyph size={20} focusable="false" {...props} />;

// navigation and controls
export const HomeIcon = sized(Home02);
export const ChevronRight = sized(UChevronRight);
export const ChevronLeft = sized(UChevronLeft);
export const ChevronDown = sized(UChevronDown);
export const ArrowLeft = sized(UArrowLeft);
export const ArrowRight = sized(UArrowRight);   // continue, start
export const Plus = sized(UPlus);               // start a new run
export const Close = sized(XClose);
export const Check = sized(UCheck);             // a control's tick: approve, save, apply, a checked box
export const Search = sized(SearchLg);
export const Swap = sized(SwitchVertical01);
export const Expand = sized(Maximize01);        // full screen
export const Shrink = sized(Minimize01);        // leave full screen

// actions and actors
export const Claude = sized(MessageChatCircle); // Claude, and only Claude
export const RequestChange = sized(MessagePlusCircle);
export const Terminal = sized(UTerminal);       // the console, and only the console
export const Preview = sized(Eye);
export const Picture = sized(Image01);          // render the whole look as one frame
export const Volume = sized(VolumeMax);         // hear the voice
export const Dice = sized(Dice3);               // a new seed
export const Moon = sized(Moon01);              // dark mode
export const Sun = sized(USun);                 // light mode
export const Refresh = sized(RefreshCw05);      // check again now

// the stages of a run
export const Palette = sized(UPalette);
export const Requirements = sized(ClipboardCheck);
export const Outline = sized(Dataflow03);
export const Script = sized(Edit05);
export const Storyboard = sized(LayoutGrid01);
export const Clapperboard = sized(UClapperboard);
export const FinalVideo = sized(PlayCircle);
export const Shuffle = sized(Shuffle01);

// facts
export const Stopwatch = sized(ClockStopwatch); // a length
export const Calendar = sized(UCalendar);       // a date
export const Film = sized(Film01);              // a video not made yet

// states (one each; config/status.tsx pairs them with words and fills)
export const Done = sized(CheckCircle);
export const Working = (props: Props) => <Loading02 size={20} focusable="false" className="icon-spin" {...props} />;
export const Pending = sized(UClock);
export const Waiting = sized(Bell01);           // waiting for you
export const Failed = sized(XCircle);
export const NotStarted = sized(Circle);
export const Info = sized(InfoCircle);
export const Warning = sized(AlertTriangle);
export const Error = sized(AlertCircle);
export const Empty = sized(Inbox01);
export const Unavailable = sized(SlashCircle01);
export const Unsupported = sized(MinusCircle);
export const Offline = sized(WifiOff);
export const Lock = sized(Lock01);

// media controls (filled)
export const Play = () => <svg viewBox="0 0 24 24" width={20} height={20} fill="currentColor" aria-hidden="true" focusable="false"><path d="M7 4.9v14.2a1 1 0 0 0 1.5.86l11.6-7.1a1 1 0 0 0 0-1.72L8.5 4.04A1 1 0 0 0 7 4.9z" /></svg>;
export const Pause = () => <svg viewBox="0 0 24 24" width={20} height={20} fill="currentColor" aria-hidden="true" focusable="false"><rect x="6" y="4.5" width="4" height="15" rx="1" /><rect x="14" y="4.5" width="4" height="15" rx="1" /></svg>;
