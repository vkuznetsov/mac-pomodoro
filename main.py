import rumps
import math
from dataclasses import dataclass
from datetime import timedelta, datetime
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


class TimerState:
    pass


@dataclass
class RunningState(TimerState):
    endTime: datetime


@dataclass
class PausedState(TimerState):
    remainingTime: timedelta


@dataclass
class StoppedState(TimerState):
    pass


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
        self.updateState(StoppedState())

    def restartTimer(self, _):
        self.updateState(RunningState(datetime.now() + self.settings.pomodoroInterval))

    def pauseTimer(self, _):
        match self.state:
            case RunningState(endTime=endTime):
                self.updateState(PausedState(endTime - datetime.now()))

    def continueTimer(self, _):
        match self.state:
            case PausedState(remainingTime=remainingTime):
                self.updateState(RunningState(datetime.now() + remainingTime))

    def clearIntervals(self, _):
        self.updatePassedIntervals(0)
        self.updateState(StoppedState())

    def updatePassedIntervals(self, newValue):
        self.passedIntervals = newValue
        self.passedItem.title = f"{newValue} interval(s) passed"

    def updateState(self, newstate: TimerState):
        self.state = newstate
        self.updateTitle()
        match newstate:
            case RunningState():
                self.pauseItem.set_callback(self.pauseTimer)
                self.continueItem.set_callback(None)
                self.timer.start()
            case PausedState():
                self.pauseItem.set_callback(None)
                self.continueItem.set_callback(self.continueTimer)
                self.timer.stop()
            case StoppedState():
                self.pauseItem.set_callback(None)
                self.continueItem.set_callback(None)
                self.timer.stop()

    def toggleState(self):
        match self.state:
            case RunningState(endTime=endTime):
                self.updateState(PausedState(endTime - datetime.now()))
            case PausedState(remainingTime=remainingTime):
                self.updateState(RunningState(datetime.now() + remainingTime))
            case StoppedState():
                self.updateState(
                    RunningState(datetime.now() + self.settings.pomodoroInterval)
                )

    def updateTitle(self):
        match self.state:
            case RunningState(endTime=endTime):
                remainingTimeStr = self.settings.displayRemainingTimeFn(
                    endTime - datetime.now()
                )
                self.title = self.settings.startSymbol + " " + remainingTimeStr
            case PausedState(remainingTime=remainingTime):
                remainingTimeStr = self.settings.displayRemainingTimeFn(remainingTime)
                self.title = self.settings.pauseSymbol + " " + remainingTimeStr
            case StoppedState():
                remainingTimeStr = self.settings.displayRemainingTimeFn(
                    self.settings.pomodoroInterval
                )
                self.title = self.settings.stopSymbol + " " + remainingTimeStr

    def tick(self, _):
        self.updateTitle()
        match self.state:
            case RunningState(endTime=endTime):
                if endTime <= datetime.now():
                    self.updateState(StoppedState())
                    self.updatePassedIntervals(self.passedIntervals + 1)
                    rumps.notification(
                        "Pomodoro", "Time out", self.passedItem.title, sound=True
                    )


if __name__ == "__main__":
    app = PomodoroStatusBarApp(Settings())

    @quickHotKey(virtualKey=kVK_ANSI_Grave, modifierMask=mask(shiftKey, optionKey))
    def toggleState() -> None:
        app.toggleState()

    app.run()
