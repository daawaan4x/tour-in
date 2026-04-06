import { h } from "preact";
import { useMemo } from "preact/hooks";
import render from "preact-render-to-string";

interface MarkerProps {
  mainColor?: string;
  middleColor?: string;
  borderColor?: string;
  borderWidth?: number;
  label?: string;
  labelColor?: string;
  showSpinner?: boolean;
  spinnerSize?: number;
  size?: number;
  className?: string;
  idSuffix?: string;
}

export type MarkerVariant = "start" | "destination";

export interface RenderMarkerHtmlOptions {
  variant: MarkerVariant;
  isActive: boolean;
  index?: number;
  isPlanning?: boolean;
  destinationId?: string;
  size?: number;
}

function markerIdSuffix({
  variant,
  destinationId,
}: Pick<RenderMarkerHtmlOptions, "variant" | "destinationId">): string {
  const rawId = destinationId ?? variant;
  const normalizedId = rawId.replace(/[^a-zA-Z0-9_-]/g, "-");
  return `${variant}-${normalizedId}`;
}

interface SpinnerProps {
  size?: number;
  color?: string;
  trackColor?: string;
  strokeWidth?: number;
}

export function Spinner({
  size = 12,
  color = "var(--color-accent-route)",
  trackColor = "rgb(47 36 29 / 28%)",
  strokeWidth = 2,
}: SpinnerProps) {
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-block",
        width: `${size}px`,
        height: `${size}px`,
        minWidth: `${size}px`,
        minHeight: `${size}px`,
        maxWidth: `${size}px`,
        maxHeight: `${size}px`,
        aspectRatio: "1 / 1",
        flexShrink: 0,
        boxSizing: "border-box",
        borderRadius: "50%",
        border: `${strokeWidth}px solid ${trackColor}`,
        borderTopColor: color,
        animation: "route-pending-spinner 620ms linear infinite",
        transformOrigin: "center center",
      }}
    />
  );
}

export function renderMarkerHtml(options: RenderMarkerHtmlOptions): string {
  const isDestination = options.variant === "destination";
  const isPlanningDestination = isDestination && Boolean(options.isPlanning);

  let mainColor = "var(--color-bg-card)";
  let middleColor = "var(--color-bg-card-muted)";
  let borderColor = "rgb(47 36 29 / 24%)";
  let labelColor = "var(--color-text-primary)";
  let label =
    isDestination && typeof options.index === "number"
      ? String(options.index + 1)
      : "S";

  if (options.variant === "start") {
    mainColor = "var(--color-brand-primary)";
    middleColor = "var(--color-text-primary)";
    borderColor = "rgb(47 36 29 / 25%)";
    labelColor = "var(--color-text-inverse)";
  }

  if (options.isActive) {
    mainColor = "var(--color-accent-route)";
    middleColor = "var(--color-text-primary)";
    borderColor = "var(--color-accent-route)";
    labelColor = "var(--color-text-inverse)";
  }

  if (isPlanningDestination) {
    label = "";
  }

  const markerMarkup = render(
    h(Marker, {
      mainColor,
      middleColor,
      borderColor,
      label,
      labelColor,
      showSpinner: isPlanningDestination,
      size: options.size ?? 40,
      idSuffix: markerIdSuffix(options),
    }),
  );

  if (!isPlanningDestination) {
    return markerMarkup;
  }

  return `${markerMarkup}<span class="sr-only">Updating stop order</span>`;
}

/**
 * Marker — pixel-accurate map pin component.
 *
 * Shape follows the silhouette in `.prompt/Google_Maps_icon_(2026).svg`.
 *
 * Props:
 *   mainColor   {string}  CSS color for the outer pin   (default: "#e63946")
 *   middleColor {string}  CSS color for inner circle    (default: "#111111")
 *   borderColor {string}  Border color of the pin        (default: "rgb(47 36 29 / 24%)")
 *   borderWidth {number}  Border width in SVG units      (default: 8)
 *   label       {string}  Text / emoji in the centre    (default: "")
 *   labelColor  {string}  Label fill color              (default: "white")
 *   size        {number}  Width & height in px          (default: 120)
 *   className   {string}  Extra Tailwind classes        (default: "")
 *   idSuffix    {string}  Stable defs/filter id suffix  (optional)
 */
export default function Marker({
  mainColor = "#e63946",
  middleColor = "#111111",
  borderColor = "rgb(47 36 29 / 24%)",
  borderWidth = 8,
  label = "",
  labelColor = "white",
  showSpinner = true,
  spinnerSize,
  size = 120,
  className = "",
  idSuffix,
}: MarkerProps) {
  const generatedId = useMemo(
    () => `mk-${Math.random().toString(36).slice(2, 8)}`,
    [],
  );
  const id = idSuffix ? `mk-${idSuffix}` : generatedId;
  const viewBoxSize = 192;
  const shadowOffset = viewBoxSize * 0.04;
  const shadowBlur = viewBoxSize * 0.04;
  const cx = 96;
  const cy = 77;
  const spinnerPixelSize = spinnerSize ?? Math.max(10, Math.round(size * 0.3));
  const spinnerStrokeWidth = Math.max(2, Math.round(spinnerPixelSize * 0.16));
  const spinnerCenterX = (cx / viewBoxSize) * size;
  const spinnerCenterY = (cy / viewBoxSize) * size;
  const innerR = 45;
  const pinPath =
    "M96,8c38.11,0,69,30.89,69,69,0,14.15-4.26,27.31-11.57,38.26-14.46,21.66-37.07,37.94-48.72,61.23l-1.54,3.07c-1.48,2.96-4.33,4.44-7.18,4.44-2.85,0-5.69-1.48-7.17-4.44l-1.54-3.07c-11.65-23.29-34.25-39.57-48.71-61.23-7.31-10.95-11.57-24.11-11.57-38.26,0-38.11,30.89-69,69-69Z";

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        position: "relative",
        display: "block",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
        xmlns="http://www.w3.org/2000/svg"
        overflow="visible"
      >
        <defs>
          <radialGradient
            id={`${id}-rg`}
            cx="50%"
            cy="35%"
            r="65%"
            fx="36%"
            fy="24%"
          >
            <stop offset="0%" stopColor={mainColor} />
            <stop offset="55%" stopColor={mainColor} />
            <stop offset="100%" stopColor={mainColor} />
          </radialGradient>
          <filter id={`${id}-f`} x="-25%" y="-10%" width="150%" height="145%">
            <feDropShadow
              dx="0"
              dy={shadowOffset}
              stdDeviation={shadowBlur}
              floodColor={mainColor}
              floodOpacity="0.35"
            />
          </filter>
        </defs>

        <g filter={`url(#${id}-f)`}>
          <path
            d={pinPath}
            fill={`url(#${id}-rg)`}
            stroke={borderColor}
            strokeWidth={borderWidth}
          />
        </g>

        <circle cx={cx} cy={cy} r={innerR} fill={middleColor} />

        {label && (
          <text
            x={cx}
            y={cy}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={innerR}
            fontFamily="system-ui, -apple-system, sans-serif"
            fontWeight="700"
            fill={labelColor}
            style={{ userSelect: "none", pointerEvents: "none" }}
          >
            {label}
          </text>
        )}
      </svg>
      {showSpinner && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            left: `${spinnerCenterX}px`,
            top: `${spinnerCenterY}px`,
            transform: "translate(-50%, -50%)",
            pointerEvents: "none",
            zIndex: 2,
            width: `${spinnerPixelSize}px`,
            height: `${spinnerPixelSize}px`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Spinner size={spinnerPixelSize} strokeWidth={spinnerStrokeWidth} />
        </div>
      )}
    </div>
  );
}
