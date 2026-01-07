"""
MCP 计算器服务器（基于 FastMCP）
提供数学计算、科学函数、统计分析和单位转换功能
"""
import math
import statistics
import ast
import operator
from typing import List, Dict, Any
from decimal import getcontext

from fastmcp import FastMCP

# 设置高精度上下文（虽未直接使用 Decimal，但保留以备扩展）
getcontext().prec = 30


# ========== 安全表达式求值器 ==========
def safe_eval_expr(expression: str) -> float:
    """使用 AST 安全解析数学表达式，仅允许数字和基本运算符"""
    # 允许的字符（防止注入）
    allowed = set("0123456789+-*/().^ ")
    if not all(c in allowed for c in expression):
        raise ValueError("表达式包含非法字符")

    expr = expression.replace("^", "**").strip()
    if not expr:
        raise ValueError("表达式不能为空")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"表达式语法错误: {e}")

    # 支持的操作符
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, (ast.Constant, ast.Num)):  # Constant for Py>=3.8, Num for older
            val = getattr(node, 'value', getattr(node, 'n', None))
            if isinstance(val, (int, float)):
                return float(val)
            raise ValueError("仅支持数值字面量")
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            return ops[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            return ops[type(node.op)](operand)
        else:
            raise ValueError(f"不支持的表达式类型: {type(node).__name__}")

    result = _eval(tree.body)
    if not math.isfinite(result):
        raise ValueError("计算结果为无穷或 NaN")
    return result


# ========== 单位转换表 ==========
CONVERSION_RATES = {
    "length": {
        "meter": 1.0,
        "kilometer": 1000.0,
        "centimeter": 0.01,
        "millimeter": 0.001,
        "mile": 1609.34,
        "yard": 0.9144,
        "foot": 0.3048,
        "inch": 0.0254
    },
    "weight": {
        "kilogram": 1.0,
        "gram": 0.001,
        "milligram": 1e-6,
        "pound": 0.453592,
        "ounce": 0.0283495
    }
}

# ========== FastMCP 服务器 ==========
mcp = FastMCP(
    name="calculator",
    instructions="提供安全的数学计算、科学函数、统计分析和单位转换服务",
    log_level="INFO"
)


# --- 工具 1: 基本计算器 ---
@mcp.tool(
    name="basic_calculator",
    description="安全计算数学表达式（支持 + - * / ^ () 和小数）"
)
async def basic_calculator(expression: str, precision: int = 6) -> dict:
    try:
        result = safe_eval_expr(expression)
        formatted = f"{result:.{precision}f}"
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "formatted_result": formatted,
            "precision": precision
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"计算失败: {str(e)}",
            "expression": expression
        }


# --- 工具 2: 科学计算器 ---
@mcp.tool(
    name="scientific_calculator",
    description="执行科学函数计算（sin/cos/tan/log/ln/exp/sqrt）"
)
async def scientific_calculator(
        function: str,
        value: float,
        angle_unit: str = "radians"
) -> dict:
    try:
        # 角度转弧度（如需要）
        calc_value = value
        if function in ("sin", "cos", "tan") and angle_unit == "degrees":
            calc_value = math.radians(value)

        # 执行函数
        funcs = {
            "sin": lambda x: math.sin(x),
            "cos": lambda x: math.cos(x),
            "tan": lambda x: math.tan(x),
            "log": lambda x: math.log10(x),
            "ln": lambda x: math.log(x),
            "exp": lambda x: math.exp(x),
            "sqrt": lambda x: math.sqrt(x),
        }

        if function not in funcs:
            raise ValueError(f"不支持的函数: {function}")

        if function in ("log", "ln", "sqrt") and value <= 0:
            raise ValueError(f"{function} 的输入必须大于 0")

        result = funcs[function](calc_value)

        if not math.isfinite(result):
            raise ValueError("结果溢出或无效")

        return {
            "success": True,
            "function": function,
            "input_value": value,
            "result": result,
            "angle_unit": angle_unit
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"科学计算失败: {str(e)}",
            "function": function,
            "input_value": value
        }


# --- 工具 3: 统计分析 ---
@mcp.tool(
    name="statistical_analysis",
    description="对数值数组进行统计分析（均值、中位数、标准差等）"
)
async def statistical_analysis(data: List[float], analysis_type: str = "all") -> dict:
    try:
        if not data:
            raise ValueError("数据列表不能为空")
        if not all(isinstance(x, (int, float)) for x in data):
            raise ValueError("数据必须全部为数字")

        n = len(data)
        results = {}

        if analysis_type in ("all", "mean"):
            results["mean"] = statistics.mean(data)
        if analysis_type in ("all", "median"):
            results["median"] = statistics.median(data)
        if analysis_type in ("all", "std"):
            results["standard_deviation"] = statistics.stdev(data) if n > 1 else 0.0
        if analysis_type in ("all", "variance"):
            results["variance"] = statistics.variance(data) if n > 1 else 0.0
        if analysis_type == "all":
            results.update({
                "min": min(data),
                "max": max(data),
                "sum": sum(data),
                "count": n
            })

        return {
            "success": True,
            "analysis_type": analysis_type,
            "data_count": n,
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"统计分析失败: {str(e)}",
            "data_sample": data[:5]  # 避免返回过长数据
        }


# --- 工具 4: 单位转换（暂不支持货币）---
@mcp.tool(
    name="unit_converter",
    description="在长度、重量、温度单位之间转换（不支持货币）"
)
async def unit_converter(
        value: float,
        from_unit: str,
        to_unit: str,
        category: str
) -> dict:
    try:
        # 温度特殊处理
        if category == "temperature":
            # 输入合法性检查
            if from_unit == "kelvin" and value < 0:
                raise ValueError("开尔文温度不能为负")
            if from_unit == "celsius" and value < -273.15:
                raise ValueError("摄氏温度不能低于 -273.15°C")
            if from_unit == "fahrenheit" and value < -459.67:
                raise ValueError("华氏温度不能低于 -459.67°F")

            # 转换逻辑
            if from_unit == to_unit:
                result = value
            elif from_unit == "celsius" and to_unit == "fahrenheit":
                result = value * 9 / 5 + 32
            elif from_unit == "fahrenheit" and to_unit == "celsius":
                result = (value - 32) * 5 / 9
            elif from_unit == "celsius" and to_unit == "kelvin":
                result = value + 273.15
            elif from_unit == "kelvin" and to_unit == "celsius":
                result = value - 273.15
            elif from_unit == "fahrenheit" and to_unit == "kelvin":
                c = (value - 32) * 5 / 9
                result = c + 273.15
            elif from_unit == "kelvin" and to_unit == "fahrenheit":
                c = value - 273.15
                result = c * 9 / 5 + 32
            else:
                raise ValueError(f"不支持的温度转换: {from_unit} → {to_unit}")

        else:
            # 长度/重量
            if category not in CONVERSION_RATES:
                raise ValueError(f"不支持的类别: {category}")
            rates = CONVERSION_RATES[category]
            if from_unit not in rates:
                raise ValueError(f"未知源单位: {from_unit}")
            if to_unit not in rates:
                raise ValueError(f"未知目标单位: {to_unit}")

            base_val = value * rates[from_unit]
            result = base_val / rates[to_unit]

        return {
            "success": True,
            "original_value": value,
            "original_unit": from_unit,
            "converted_value": round(result, 10),
            "converted_unit": to_unit,
            "category": category
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"单位转换失败: {str(e)}",
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "category": category
        }


# ========== 启动入口 ==========
if __name__ == "__main__":
    print("🧮 启动 FastMCP 计算器服务器...")
    print("💡 支持工具: basic_calculator, scientific_calculator, statistical_analysis, unit_converter")
    mcp.run()