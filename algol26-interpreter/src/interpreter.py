    def eval_SelectStmt(self, stmt: SelectStmt):
        ready_cases = []

        for case in stmt.cases:
            ch = self.eval(case.channel)
            if not isinstance(ch, Chan):
                raise InterpreterError(f"Case channel must be a Chan, got {type(ch)}")
            if case.is_send:
                continue  # Send case handling pending
            else:  # Receive case
                val = ch.try_recv()
                if val is not None:
                    ready_cases.append((case, val))

        if ready_cases:
            for case, val in ready_cases:
                self.eval(case.stmt)  # FYI: No env binding yet
                break
        elif stmt.default_stmt:
            self.eval(stmt.default_stmt)