# Technical Requirements
- Use `uv` to manage dependencies. Always use `uv run`, `uv add` etc instead of running Python or pip directly.
- Respect Python idioms: All Python source code should be placed inside the `src/package_name/` directory. Test code should be in the `src/test/` directory.
- Unless there is a strong reason, add import statements at the top of your module.
- Use type annotations for function arguments.
- Add docstrings for all functions more than 5 lines of code.
- Add unit tests for every module you write.
- After adding features, remember to update / run unit tests.
