'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { FileText, LayoutDashboard, Settings, LogOut, Moon, Sun, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { useAuthStore } from '@/lib/store/authStore'
import { useThemeStore } from '@/lib/store/themeStore'
import { cn } from '@/lib/utils/cn'

interface SidebarProps {
  mobileOpen?: boolean
  onMobileOpenChange?: (open: boolean) => void
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
]

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <>
      {navigation.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-[13px] font-mono uppercase tracking-wider transition-colors',
              isActive
                ? 'text-primary border-b-2 border-primary'
                : 'text-muted-foreground hover:text-primary border-b-2 border-transparent'
            )}
          >
            <item.icon className="h-4 w-4" />
            <span>{item.name}</span>
          </Link>
        )
      })}
    </>
  )
}

function MobileNavContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <>
      <div className="p-6 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2" onClick={onNavigate}>
          <FileText className="h-6 w-6 text-primary" />
          <span className="font-mono uppercase tracking-wider text-sm font-bold text-foreground">BRD Generator</span>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-3 px-4 py-3 text-[13px] font-mono uppercase tracking-wider transition-colors',
                isActive
                  ? 'text-primary border-l-[3px] border-primary bg-primary/5'
                  : 'text-muted-foreground hover:text-primary border-l-[3px] border-transparent'
              )}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary/10 flex items-center justify-center border border-primary/30">
              <span className="text-xs font-mono font-bold text-primary">
                {user?.display_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user?.display_name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
        <Button variant="outline" className="w-full justify-start" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </>
  )
}

export function Sidebar({ mobileOpen, onMobileOpenChange }: SidebarProps) {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <>
      {/* Desktop top nav bar */}
      <header className="hidden md:flex items-center h-14 px-6 border-b border-border/50 bg-background/60 backdrop-blur-xl shrink-0">
        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2 mr-8">
          <FileText className="h-5 w-5 text-primary" />
          <span className="font-mono uppercase tracking-wider text-[13px] font-bold text-foreground">
            BRD Generator
          </span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          <NavLinks />
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right side: user controls */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8">
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          <div className="w-px h-6 bg-border mx-1" />

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-primary/10 flex items-center justify-center border border-primary/30">
              <span className="text-[11px] font-mono font-bold text-primary">
                {user?.display_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="text-[13px] font-mono text-muted-foreground">
              {user?.display_name}
            </span>
          </div>

          <Button variant="ghost" size="icon" onClick={handleLogout} className="h-8 w-8" title="Logout">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {/* Mobile: hamburger + sheet */}
      <header className="md:hidden flex items-center gap-3 h-12 px-4 border-b border-border/50 bg-background/60 backdrop-blur-xl shrink-0">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onMobileOpenChange?.(true)}>
          <Menu className="h-5 w-5" />
        </Button>
        <Link href="/dashboard" className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <span className="font-mono uppercase tracking-wider text-[13px] font-bold">BRD Generator</span>
        </Link>
      </header>

      <Sheet open={mobileOpen} onOpenChange={onMobileOpenChange}>
        <SheetContent side="left" className="w-64 p-0 flex flex-col">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <MobileNavContent onNavigate={() => onMobileOpenChange?.(false)} />
        </SheetContent>
      </Sheet>
    </>
  )
}
