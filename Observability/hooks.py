from .metrics import *
from typing import Any, Optional

# Logger for Hooks
from .logging import StructuredLogger


class ObservabilityHooks:
    """
    Central lifecycle hook interface for observability.

    Components call these hooks when important events happen.
    The hooks update Prometheus metrics and structured logs
    without exposing Prometheus-specific logic to the rest
    of the application.
    """

    def __init__(self):
        self.logger = StructuredLogger()

    # ============================================================
    # Agent Lifecycle
    # ============================================================

    def agent_start(self, run_id: str) -> None:
        """
        Anytime an agent starts:
        - Increment total agent runs
        - Increment active agent runs
        - Write structured log
        """

        AGENT_RUNS_TOTAL.inc()
        AGENT_ACTIVE_RUNS.inc()

#        self.logger.log(
 #           "agent_started",
  #          run_id,
   #         component="agent",
    #    )

    def agent_finish(
        self,
        run_id: str,
        duration_secs: float,
        success: bool = True,
    ) -> None:
        """
        Anytime an agent finishes:
        - Decrement active runs
        - Record duration
        - Record failure if necessary
        - Write structured log
        """

        AGENT_ACTIVE_RUNS.dec()
        AGENT_RUN_DURATION.observe(duration_secs)

        if not success:
            AGENT_RUN_FAILURES_TOTAL.inc()

#        self.logger.log(
 #           "agent_finished",
  #          run_id,
   #         component="agent",
    #        status="success" if success else "error",
     #       Duration_seconds=duration_secs,
      #  )

    # ============================================================
    # LLM Lifecycle
    # ============================================================

    def LLM_start(self, run_id: str) -> None:
        """
        Anytime an LLM call starts:
        - Increment total LLM calls
        - Write structured log
        """

        LLM_CALLS_TOTAL.inc()

#        self.logger.log(
 #           "llm_started",
  #          run_id,
   #         component="llm",
    #    )

    def LLM_finish(
        self,
        run_id: str,
        duration_secs: float,
        input_tkns: Optional[int] = None,
        output_tkns: Optional[int] = None,
    ) -> None:
        """
        Anytime an LLM call finishes:
        - Record duration
        - Record input tokens
        - Record output tokens
        - Write structured log
        """

        LLM_CALL_DURATION.observe(duration_secs)

        if input_tkns is not None:
            LLM_INPUT_TOKENS_TOTAL.inc(input_tkns)

        if output_tkns is not None:
            LLM_OUTPUT_TOKENS_TOTAL.inc(output_tkns)

#        self.logger.log(
 #           "llm_finished",
  #          run_id,
   #         component="llm",
    #        Duration_seconds=duration_secs,
     #       Input_tokens=input_tkns,
      #      Output_tokens=output_tkns,
       # )

    def llm_error(
        self,
        run_id: str,
        component: str,
        error: str,
    ) -> None:
        """
        Record an LLM call that raised an exception.
        """

        LLM_ERRORS_TOTAL.labels(
            component=component
        ).inc()

#        self.logger.log(
 #           "llm_error",
  #          run_id,
   #         level="ERROR",
    ##        component=component,
      #      status="error",
       #     Error=error,
        #)

    # ============================================================
    # Tool Lifecycle
    # ============================================================

    def Tool_start(
        self,
        run_id: str,
        tool_name: str,
        tool_type: str,
    ) -> None:
        """
        Anytime a tool starts:
        - Increment total tool calls
        - Write structured log
        """

        TOOL_CALLS_TOTAL.labels(
            tool_name=tool_name,
            tool_type=tool_type,
        ).inc()

#        self.logger.log(
 #           "tool_start",
  #          run_id,
   #         component="tool",
    #        Tool_name=tool_name,
     #       Tool_type=tool_type,
      #  )

    def Tool_finish(
        self,
        run_id: str,
        tool_name: str,
        tool_type: str,
        duration_secs: float,
        success: bool,
    ) -> None:
        """
        Anytime a tool finishes:
        - Record duration
        - Record success/failure
        - Write structured log
        """

        TOOL_CALL_DURATION.labels(
            tool_name=tool_name,
            tool_type=tool_type,
        ).observe(duration_secs)

        if success:
            TOOL_SUCCESS_TOTAL.labels(
                tool_name=tool_name,
                tool_type=tool_type,
            ).inc()
        else:
            TOOL_FAILURE_TOTAL.labels(
                tool_name=tool_name,
                tool_type=tool_type,
            ).inc()

#        self.logger.log(
 #           "tool_finish",
  #          run_id,
   #         component="tool",
    #        Duration_seconds=duration_secs,
     #       Tool_name=tool_name,
      #      Tool_type=tool_type,
       #     Result=success,
       # )

    # ============================================================
    # Memory Lifecycle
    # ============================================================

    def memo_op(
        self,
        run_id: str,
        operation: str,
    ) -> None:
        """
        Anytime the memory system is interacted with:
        - Increment memory operation counter
        - Write structured log
        """

        MEMORY_OPERATIONS_TOTAL.inc()

#        self.logger.log(
 #           "memory_operation",
  #          run_id,
   #         component="memory",
    #        Operation_name=operation,
     #   )

    def memo_retrieval_finish(
        self,
        run_id: str,
        duration_secs: float,
    ) -> None:
        """
        Anytime memory retrieval finishes:
        - Record retrieval duration
        - Write structured log
        """

        MEMORY_RETRIEVAL_DURATION.observe(duration_secs)

#        self.logger.log(
 #           "memory_operation_finished",
  #          run_id,
   #         component="memory",
    #        Duration_seconds=duration_secs,
     #   )

    # ============================================================
    # Permission Lifecycle
    # ============================================================

    def permission_decision(
        self,
        run_id: str,
        tool_name: str,
        tool_type: str,
        decision: str,
        duration_secs: Optional[float] = None,
    ) -> None:
        """
        Record a permission decision and optionally its duration.
        """

        PERMISSION_DECISIONS_TOTAL.labels(
            tool_name=tool_name,
            tool_type=tool_type,
            decision=decision,
        ).inc()

        if duration_secs is not None:
            PERMISSION_CHECK_DURATION.labels(
                tool_name=tool_name,
                tool_type=tool_type,
            ).observe(duration_secs)

#        self.logger.log(
 #           "permission_decision",
  #          run_id,
   ##         component="permission",
     #       status=decision,
      #      tool_name=tool_name,
       #     tool_type=tool_type,
        #    decision=decision,
        #    Duration_seconds=duration_secs,
        #)

    # ============================================================
    # Planner Lifecycle
    # ============================================================

    def planner_start(
        self,
        run_id: str,
        operation: str,
    ) -> None:
        """
        Anytime a planner operation starts.
        """

#        self.logger.log(
 #           "planner_start",
  #          run_id,
   #         component="planner",
    #        Operation=operation,
     #   )

    def planner_finish(
        self,
        run_id: str,
        operation: str,
        duration_secs: float,
        success: bool,
    ) -> None:
        """
        Anytime a planner operation finishes:
        - Record duration
        - Record errors
        - Write structured log
        """

        PLANNER_DURATION.labels(
            operation=operation
        ).observe(duration_secs)

        if not success:
            PLANNER_ERRORS_TOTAL.labels(
                operation=operation
            ).inc()

#        self.logger.log(
 #           "planner_finish",
  #          run_id,
   #         component="planner",
    #        status="success" if success else "error",
     #       Operation=operation,
      #      Duration_seconds=duration_secs,
       # )

    # ============================================================
    # Sub-Agent Lifecycle
    # ============================================================

    def subagent_start(
        self,
        run_id: str,
        subagent_type: str,
    ) -> None:
        """
        Anytime a sub-agent starts:
        - Increment total sub-agent runs
        - Increment active sub-agent runs
        - Write structured log
        """

        SUBAGENT_RUNS_TOTAL.labels(
            subagent_type=subagent_type
        ).inc()

        SUBAGENT_ACTIVE_RUNS.inc()

#        self.logger.log(
 #           "subagent_start",
  #          run_id,
   #         component="subagent",
    #        Subagent_type=subagent_type,
     #   )

    def subagent_finish(
        self,
        run_id: str,
        subagent_type: str,
        duration_secs: float,
        success: bool,
    ) -> None:
        """
        Anytime a sub-agent finishes:
        - Decrement active sub-agent runs
        - Record duration
        - Record failures
        - Write structured log
        """

        SUBAGENT_ACTIVE_RUNS.dec()

        SUBAGENT_RUN_DURATION.labels(
            subagent_type=subagent_type
        ).observe(duration_secs)

        if not success:
            SUBAGENT_FAILURES_TOTAL.labels(
                subagent_type=subagent_type
            ).inc()

#        self.logger.log(
 #           "subagent_finish",
  #          run_id,
   #         component="subagent",
    #        status="success" if success else "error",
     #       Subagent_type=subagent_type,
      #      Duration_seconds=duration_secs,
       # )