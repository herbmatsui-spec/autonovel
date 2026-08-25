import * as React from "react"
import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"
import { buttonVariants, type ButtonVariants } from "./buttonVariants"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    ButtonVariants {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        // Accessibility: Ensure buttons have a descriptive label if they only contain an icon
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
export type { ButtonVariants } from "./buttonVariants"
