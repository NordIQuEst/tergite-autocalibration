# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import ast
import inspect
import textwrap
from typing import Set


class ASTParser:
    @staticmethod
    def get_init_attribute_names(cls) -> Set[str]:
        try:
            # Try to get the source code of the class
            source = inspect.getsource(cls)
            # Dedent the source to handle indented classes
            source = textwrap.dedent(source)
        except (TypeError, OSError, IndentationError) as e:
            # Handle errors in retrieving the source
            print(f"Error retrieving source for {cls.__name__}: {e}")
            return set()

        try:
            # Parse the source code into an AST
            tree = ast.parse(source)
        except SyntaxError as e:
            # Handle parsing errors
            print(f"Syntax error when parsing source of {cls.__name__}: {e}")
            return set()

        # Find the class definition
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == cls.__name__:
                # Look for the __init__ method
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                        # Collect all assignments to 'self.<attribute>'
                        attributes = set()
                        for stmt in child.body:
                            # Handle `Assign`, this is for normal variables e.g. self.var1 = 0
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if (
                                        isinstance(target, ast.Attribute)
                                        and isinstance(target.value, ast.Name)
                                        and target.value.id == "self"
                                    ):
                                        attributes.add(target.attr)
                            # Handle `AnnAssign`, this is for annotated variables e.g. self.var1: int = 0
                            elif isinstance(stmt, ast.AnnAssign):
                                if (
                                    isinstance(stmt.target, ast.Attribute)
                                    and isinstance(stmt.target.value, ast.Name)
                                    and stmt.target.value.id == "self"
                                ):
                                    attributes.add(stmt.target.attr)
                        return attributes
        return set()
