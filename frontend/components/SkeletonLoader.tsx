import React from "react";
import "../styles/dashboard_components.css";

interface SkeletonLoaderProps {
  width?: string;
  height?: string;
  borderRadius?: string;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  width = "100%",
  height = "20px",
  borderRadius = "8px",
}) => {
  return (
    <div
      className="skeleton-loader-shimmer"
      style={{ width, height, borderRadius }}
    />
  );
};

export default SkeletonLoader;
