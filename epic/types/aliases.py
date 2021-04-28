from typing import Tuple, List, Optional, Callable, Union

from epic.types.classes import RCDMessage

HandlerResult = Tuple[List[Union[RCDMessage, str]], Tuple[Optional[Callable], tuple]]
