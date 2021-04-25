from typing import Tuple, List, Optional, Callable

from epic.types.classes import RCDMessage

HandlerResult = Tuple[List[RCDMessage], Tuple[Optional[Callable], tuple]]
