// The Faraday logo (white on transparent, from the brand banner): the F mark, a rule and the wordmark.
import logo from "../../assets/faraday-logo.webp";

export function Logo({ height = 22 }: { height?: number }) {
  return <img className="logo" src={logo} alt="Faraday" height={height} width={Math.round(height * 733 / 96)} />;
}
