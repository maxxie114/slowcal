import Image, { ImageProps } from "next/image";
import { cn } from "@/lib/utils";
import { TapeStrip } from "./TapeStrip";

interface PolaroidImageProps extends Omit<ImageProps, "alt"> {
    alt: string;
    caption?: string;
    tape?: boolean;
    containerClassName?: string;
    rotation?: "left" | "right" | "none";
}

export function PolaroidImage({
    src,
    alt,
    caption,
    tape = true,
    rotation = "left",
    containerClassName,
    className,
    ...props
}: PolaroidImageProps) {
    const rotationClasses = {
        left: "-rotate-2",
        right: "rotate-2",
        none: "rotate-0",
    };

    return (
        <div
            className={cn(
                "relative inline-block bg-white p-3 pb-8 shadow-polaroid transition-transform hover:scale-[1.02] hover:z-10",
                rotationClasses[rotation],
                containerClassName
            )}
        >
            {tape && <TapeStrip variant="horizontal" className="left-1/2 -translate-x-1/2 -top-4 w-24 opacity-90" />}

            <div className="relative overflow-hidden bg-gray-100 aspect-square">
                <Image
                    src={src}
                    alt={alt}
                    className={cn("object-cover", className)}
                    {...props}
                />
            </div>

            {caption && (
                <p className="mt-3 text-center font-script text-xl text-ink-medium leading-none">
                    {caption}
                </p>
            )}
        </div>
    );
}
