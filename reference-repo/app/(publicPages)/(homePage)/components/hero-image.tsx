interface HeroImageProps {
    className?: string;
}

export function HeroImage({ className = "" }: HeroImageProps) {
    return (
        <div className={`relative ${className}`}>
            <video
                className="w-full h-auto object-cover"
                autoPlay
                loop
                muted
                playsInline
                preload="metadata"
                poster="/parliament.jpg"
                aria-label="Parliament building representing democratic governance and political discourse"
            >
                <source
                    src="https://thempai.lon1.cdn.digitaloceanspaces.com/websiteAssets/houses-of-parliament-london-uk-after-major-refurbi-4k-2025-08-29-00-18-26-utc.mp4"
                    type="video/mp4"
                />
                Your browser does not support the video tag.
            </video>
        </div>
    );
}
