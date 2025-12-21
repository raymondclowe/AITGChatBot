# LaTeX Formatting Instructions for AI Models

When providing mathematical formulas or equations in your responses, please format them using one of these three supported LaTeX formats:

## 1. Code Block Format (Recommended for complex equations):
```latex
your_latex_code_here
```

## 2. Display Math Format (For standalone equations):
$$your_latex_code_here$$

## 3. LaTeX Display Format (Alternative display format):
\[your_latex_code_here\]

## Examples:

### Quadratic Formula:
```latex
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
```

### Einstein's Equation:
$$E = mc^2$$

### Matrix:
\[\begin{pmatrix} a & b \\ c & d \end{pmatrix}\]

### More Complex Examples:

#### Integral:
```latex
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
```

#### Summation:
$$\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$$

#### Limit:
\[\lim_{x \to 0} \frac{\sin x}{x} = 1\]

## Important Notes:
- Use standard LaTeX math syntax without document headers
- Each LaTeX block will be automatically rendered as an image
- Text before and after LaTeX blocks will be sent as regular messages
- If rendering fails, the LaTeX code will be sent as a formatted code block instead

## What NOT to do:
- Don't use single dollar signs `$...$` for inline math (not supported)
- Don't include LaTeX document structure commands like `\documentclass`, `\begin{document}`, etc.
- Don't nest LaTeX blocks within each other