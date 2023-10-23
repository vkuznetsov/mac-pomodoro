import rumps
import math
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Callable
from quickmachotkey import quickHotKey, mask
from quickmachotkey.constants import optionKey, shiftKey, kVK_ANSI_Grave


@dataclass
class Settings:
    startSymbol: str = "▶"
    pauseSymbol: str = "⏸"
    restartSymbol: str = "↻"
    stopSymbol: str = "⏹"
    pomodoroInterval: timedelta = timedelta(minutes=25)
    tickInterval: timedelta = timedelta(seconds=10)
    displayRemainingTimeFn: Callable[[timedelta], str] = (
        lambda td: str(math.ceil(td.seconds / 60)) + "m"
    )


class State(Enum):
    RUNNING = 1
    PAUSED = 2
    STOPPED = 3


class PomodoroStatusBarApp(rumps.App):
    def __init__(self, settings: Settings):
        super().__init__("Pomodoro")

        self.restartItem = rumps.MenuItem(
            settings.restartSymbol + " Restart", callback=self.restartTimer
        )
        self.pauseItem = rumps.MenuItem(
            settings.pauseSymbol + " Pause", callback=self.pauseTimer
        )
        self.continueItem = rumps.MenuItem(
            settings.startSymbol + " Continue", callback=self.continueTimer
        )

        self.passedItem = rumps.MenuItem("intervals", callback=self.clearIntervals)
        self.updatePassedIntervals(0)

        self.menu.add(self.restartItem)
        self.menu.add(self.pauseItem)
        self.menu.add(self.continueItem)
        self.menu.add(rumps.separator)
        self.menu.add(self.passedItem)

        self.timer = rumps.Timer(self.tick, settings.tickInterval.seconds)
        self.settings = settings
        self.restartTimer(None)


    def restartTimer(self, _):
        self.resetRemainingTicks()
        self.updateState(State.RUNNING)

    def pauseTimer(self, _):
        self.updateState(State.PAUSED)

    def continueTimer(self, _):
        self.updateState(State.RUNNING)

    def pause(self, _):
        self.menu["Start"].state = not self.menu["Start"].state

    def clearIntervals(self, _):
        self.updatePassedIntervals(0)
        self.resetRemainingTicks()
        self.updateState(State.STOPPED)

    def updatePassedIntervals(self, newValue):
        self.passedIntervals = newValue
        self.passedItem.title = f"{newValue} interval(s) passed"

    def updateState(self, newstate: State):
        self.state = newstate
        self.updateTitle()
        match newstate:
            case State.RUNNING:
                self.pauseItem.set_callback(self.pauseTimer)
                self.continueItem.set_callback(None)
                self.timer.start()
            case State.PAUSED:
                self.pauseItem.set_callback(None)
                self.continueItem.set_callback(self.continueTimer)
                self.timer.stop()
            case State.STOPPED:
                self.pauseItem.set_callback(None)
                self.continueItem.set_callback(None)
                self.timer.stop()

    def toggleState(self):
        match self.state:
            case State.RUNNING:
                self.updateState(State.PAUSED)
            case State.PAUSED | State.STOPPED:
                self.updateState(State.RUNNING)

    def updateTitle(self):
        remainingTimeStr = self.settings.displayRemainingTimeFn(self.remainingTicks * self.settings.tickInterval)
        match self.state:
            case State.RUNNING:
                self.title = self.settings.startSymbol + " " + remainingTimeStr
            case State.PAUSED:
                self.title = self.settings.pauseSymbol + " " + remainingTimeStr
            case State.STOPPED:
                self.title = self.settings.stopSymbol + " " + remainingTimeStr

    def resetRemainingTicks(self):
        self.remainingTicks = math.ceil(self.settings.pomodoroInterval / self.settings.tickInterval)

    def tick(self, _):
        self.updateTitle()
        if self.state == State.RUNNING:
            self.remainingTicks -= 1
            if self.remainingTicks < 0:
                self.resetRemainingTicks()
                self.updateState(State.STOPPED)
                self.updatePassedIntervals(self.passedIntervals + 1)
                rumps.notification("Pomodoro", "Time out", self.passedItem.title, sound=True)


if __name__ == "__main__":
    app = PomodoroStatusBarApp(Settings())

    @quickHotKey(virtualKey=kVK_ANSI_Grave, modifierMask=mask(shiftKey, optionKey))
    def toggleState() -> None:
        app.toggleState()

    app.run()
