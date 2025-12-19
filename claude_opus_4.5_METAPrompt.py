#!/usr/bin/env python3
"""
正七边形弹跳球物理模拟器 (Heptagon Bouncing Balls Simulator)
============================================================

功能特性：
- 正七边形容器以15°/秒顺时针旋转
- 20个随机颜色的弹跳球
- 完整物理模拟：重力、碰撞检测、能量损失
- 球与边界、球与球之间的精确碰撞
- 轨迹跟踪、FPS监控、鼠标交互

控制键：
- 空格键：暂停/恢复
- R键：重置所有球
- ESC键：退出
- 鼠标左键：添加新球

作者：Claude AI
"""

import pygame
import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple
from collections import deque

# ============================================================================
# 常量定义
# ============================================================================

# 窗口设置
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60

# 七边形设置
HEPTAGON_SIDES = 7
HEPTAGON_RADIUS = 300
HEPTAGON_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
ROTATION_SPEED = 15  # 度/秒（顺时针为正）

# 球的设置
BALL_RADIUS = 8
INITIAL_BALL_COUNT = 20
TRAIL_LENGTH = 100  # 轨迹长度（帧数）

# 物理常量
GRAVITY = 9.81 * 100  # 像素/秒² (放大以适应屏幕尺度)
RESTITUTION = 0.85    # 弹性系数（能量保留比例）
FRICTION = 0.995      # 空气阻力模拟

# 颜色定义
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_HEPTAGON = (100, 150, 255)
COLOR_TEXT = (200, 200, 200)


# ============================================================================
# 数学工具函数
# ============================================================================

def rotate_point(point: Tuple[float, float], 
                 center: Tuple[float, float], 
                 angle_rad: float) -> Tuple[float, float]:
    """
    将点绕中心旋转指定角度
    
    参数:
        point: 原始点坐标 (x, y)
        center: 旋转中心 (cx, cy)
        angle_rad: 旋转角度（弧度，正值为逆时针）
    
    返回:
        旋转后的点坐标
    """
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    # 平移到原点
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    
    # 旋转
    new_x = dx * cos_a - dy * sin_a
    new_y = dx * sin_a + dy * cos_a
    
    # 平移回去
    return (new_x + center[0], new_y + center[1])


def get_heptagon_vertices(center: Tuple[float, float], 
                          radius: float, 
                          rotation_angle: float) -> List[Tuple[float, float]]:
    """
    计算正七边形的顶点坐标
    
    参数:
        center: 中心点坐标
        radius: 外接圆半径
        rotation_angle: 当前旋转角度（弧度）
    
    返回:
        顶点坐标列表
    """
    vertices = []
    angle_step = 2 * math.pi / HEPTAGON_SIDES
    
    # 从正上方开始（-π/2偏移）
    start_angle = -math.pi / 2 + rotation_angle
    
    for i in range(HEPTAGON_SIDES):
        angle = start_angle + i * angle_step
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        vertices.append((x, y))
    
    return vertices


def point_to_line_distance(point: Tuple[float, float],
                           line_start: Tuple[float, float],
                           line_end: Tuple[float, float]) -> Tuple[float, Tuple[float, float]]:
    """
    计算点到线段的距离和最近点
    
    返回:
        (距离, 最近点坐标)
    """
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    # 线段向量
    dx = x2 - x1
    dy = y2 - y1
    
    # 线段长度的平方
    length_sq = dx * dx + dy * dy
    
    if length_sq < 1e-10:
        # 线段退化为点
        return math.sqrt((px - x1)**2 + (py - y1)**2), (x1, y1)
    
    # 投影参数 t (限制在 [0, 1] 范围内)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    
    # 最近点
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # 距离
    dist = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    return dist, (closest_x, closest_y)


def get_edge_normal(line_start: Tuple[float, float],
                    line_end: Tuple[float, float],
                    center: Tuple[float, float]) -> Tuple[float, float]:
    """
    获取边的内法向量（指向多边形内部）
    """
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    
    # 垂直向量（有两个方向）
    nx1, ny1 = -dy, dx
    nx2, ny2 = dy, -dx
    
    # 归一化
    length = math.sqrt(nx1**2 + ny1**2)
    if length < 1e-10:
        return (0, 0)
    
    nx1 /= length
    ny1 /= length
    nx2 /= length
    ny2 /= length
    
    # 选择指向中心的那个
    mid_x = (line_start[0] + line_end[0]) / 2
    mid_y = (line_start[1] + line_end[1]) / 2
    
    to_center_x = center[0] - mid_x
    to_center_y = center[1] - mid_y
    
    if nx1 * to_center_x + ny1 * to_center_y > 0:
        return (nx1, ny1)
    else:
        return (nx2, ny2)


def random_color() -> Tuple[int, int, int]:
    """生成随机明亮颜色"""
    # 使用HSV空间确保颜色明亮
    hue = random.random()
    saturation = 0.7 + random.random() * 0.3
    value = 0.8 + random.random() * 0.2
    
    # HSV to RGB
    c = value * saturation
    x = c * (1 - abs((hue * 6) % 2 - 1))
    m = value - c
    
    if hue < 1/6:
        r, g, b = c, x, 0
    elif hue < 2/6:
        r, g, b = x, c, 0
    elif hue < 3/6:
        r, g, b = 0, c, x
    elif hue < 4/6:
        r, g, b = 0, x, c
    elif hue < 5/6:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


# ============================================================================
# 球类
# ============================================================================

@dataclass
class Ball:
    """弹跳球类"""
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: float = BALL_RADIUS
    color: Tuple[int, int, int] = field(default_factory=random_color)
    trail: deque = field(default_factory=lambda: deque(maxlen=TRAIL_LENGTH))
    spin: float = 0.0  # 自旋角速度（弧度/秒）
    angle: float = 0.0  # 当前自旋角度
    
    def update_physics(self, dt: float):
        """更新物理状态（重力和运动）"""
        # 应用重力
        self.vy += GRAVITY * dt
        
        # 应用空气阻力
        self.vx *= FRICTION
        self.vy *= FRICTION
        self.spin *= FRICTION
        
        # 更新位置
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # 更新自旋角度
        self.angle += self.spin * dt
        
        # 记录轨迹
        self.trail.append((self.x, self.y))
    
    def get_speed(self) -> float:
        """获取当前速度大小"""
        return math.sqrt(self.vx**2 + self.vy**2)


# ============================================================================
# 物理引擎
# ============================================================================

class PhysicsEngine:
    """物理引擎：处理所有碰撞检测和响应"""
    
    def __init__(self, center: Tuple[float, float], radius: float):
        self.center = center
        self.radius = radius
        self.rotation_angle = 0.0  # 当前旋转角度（弧度）
    
    def update_rotation(self, dt: float):
        """更新七边形旋转角度"""
        # 顺时针旋转，所以是负值
        self.rotation_angle -= math.radians(ROTATION_SPEED) * dt
    
    def get_vertices(self) -> List[Tuple[float, float]]:
        """获取当前七边形顶点"""
        return get_heptagon_vertices(self.center, self.radius, self.rotation_angle)
    
    def check_ball_wall_collision(self, ball: Ball) -> bool:
        """
        检测并处理球与七边形边界的碰撞
        
        核心算法：
        1. 遍历七边形的每条边
        2. 计算球心到边的距离
        3. 如果距离小于球半径，发生碰撞
        4. 计算反弹速度（考虑旋转边界的速度）
        """
        vertices = self.get_vertices()
        collided = False
        
        for i in range(HEPTAGON_SIDES):
            # 获取边的两个端点
            p1 = vertices[i]
            p2 = vertices[(i + 1) % HEPTAGON_SIDES]
            
            # 计算球心到边的距离
            dist, closest = point_to_line_distance((ball.x, ball.y), p1, p2)
            
            if dist < ball.radius:
                collided = True
                
                # 获取边的内法向量
                normal = get_edge_normal(p1, p2, self.center)
                
                # 计算穿透深度
                penetration = ball.radius - dist
                
                # 将球推出边界
                ball.x += normal[0] * penetration * 1.01
                ball.y += normal[1] * penetration * 1.01
                
                # === 关键：计算旋转边界在碰撞点的速度 ===
                # 边界点相对于中心的位置
                rx = closest[0] - self.center[0]
                ry = closest[1] - self.center[1]
                
                # 边界点的切向速度（角速度 × 半径，垂直于半径方向）
                # ω = -ROTATION_SPEED (顺时针为负)
                omega = -math.radians(ROTATION_SPEED)
                wall_vx = -omega * ry  # 切向速度的x分量
                wall_vy = omega * rx   # 切向速度的y分量
                
                # 计算球相对于边界的速度
                rel_vx = ball.vx - wall_vx
                rel_vy = ball.vy - wall_vy
                
                # 计算相对速度在法向量上的分量
                dot = rel_vx * normal[0] + rel_vy * normal[1]
                
                # 只有当球朝向边界移动时才反弹
                if dot < 0:
                    # 反弹：反转法向速度分量，应用弹性系数
                    ball.vx -= (1 + RESTITUTION) * dot * normal[0]
                    ball.vy -= (1 + RESTITUTION) * dot * normal[1]
                    
                    # 添加边界速度的影响（能量传递）
                    ball.vx += wall_vx * (1 - RESTITUTION) * 0.5
                    ball.vy += wall_vy * (1 - RESTITUTION) * 0.5
                    
                    # 计算自旋效果
                    tangent = (-normal[1], normal[0])
                    tangent_vel = rel_vx * tangent[0] + rel_vy * tangent[1]
                    ball.spin += tangent_vel * 0.1 / ball.radius
        
        return collided
    
    def check_ball_ball_collision(self, balls: List[Ball]):
        """
        检测并处理球与球之间的碰撞
        
        使用动量守恒和能量损失公式：
        v1' = v1 - (1+e) * m2/(m1+m2) * <v1-v2, x1-x2>/|x1-x2|² * (x1-x2)
        v2' = v2 - (1+e) * m1/(m1+m2) * <v2-v1, x2-x1>/|x2-x1|² * (x2-x1)
        
        假设所有球质量相同（m1 = m2）
        """
        n = len(balls)
        
        for i in range(n):
            for j in range(i + 1, n):
                ball1 = balls[i]
                ball2 = balls[j]
                
                # 计算两球心距离
                dx = ball2.x - ball1.x
                dy = ball2.y - ball1.y
                dist_sq = dx * dx + dy * dy
                min_dist = ball1.radius + ball2.radius
                
                if dist_sq < min_dist * min_dist and dist_sq > 1e-10:
                    dist = math.sqrt(dist_sq)
                    
                    # 碰撞法向量（从ball1指向ball2）
                    nx = dx / dist
                    ny = dy / dist
                    
                    # 相对速度
                    dvx = ball1.vx - ball2.vx
                    dvy = ball1.vy - ball2.vy
                    
                    # 相对速度在碰撞法向上的分量
                    dvn = dvx * nx + dvy * ny
                    
                    # 只有当两球相向运动时才处理碰撞
                    if dvn > 0:
                        # 等质量弹性碰撞公式（带能量损失）
                        impulse = (1 + RESTITUTION) * dvn / 2
                        
                        ball1.vx -= impulse * nx
                        ball1.vy -= impulse * ny
                        ball2.vx += impulse * nx
                        ball2.vy += impulse * ny
                        
                        # 分离两球（防止粘连）
                        overlap = min_dist - dist
                        ball1.x -= nx * overlap / 2 * 1.01
                        ball1.y -= ny * overlap / 2 * 1.01
                        ball2.x += nx * overlap / 2 * 1.01
                        ball2.y += ny * overlap / 2 * 1.01
                        
                        # 交换部分自旋
                        spin_transfer = (ball1.spin - ball2.spin) * 0.3
                        ball1.spin -= spin_transfer
                        ball2.spin += spin_transfer
    
    def is_point_inside(self, x: float, y: float) -> bool:
        """检查点是否在七边形内部"""
        vertices = self.get_vertices()
        
        # 使用射线法
        inside = False
        n = len(vertices)
        j = n - 1
        
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside


# ============================================================================
# 主模拟器类
# ============================================================================

class HeptagonSimulator:
    """主模拟器：管理整个模拟过程"""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("正七边形弹跳球模拟器 - Space:暂停 R:重置 ESC:退出 点击:添加球")
        
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 48)
        
        self.physics = PhysicsEngine(HEPTAGON_CENTER, HEPTAGON_RADIUS)
        self.balls: List[Ball] = []
        self.paused = False
        self.running = True
        self.show_trails = True
        
        # FPS统计
        self.fps_history = deque(maxlen=60)
        
        # 初始化球
        self.reset_balls()
    
    def reset_balls(self):
        """重置所有球到随机位置"""
        self.balls.clear()
        
        for _ in range(INITIAL_BALL_COUNT):
            self.add_ball_random()
    
    def add_ball_random(self):
        """在七边形内添加一个随机位置的球"""
        max_attempts = 100
        
        for _ in range(max_attempts):
            # 在七边形内生成随机位置
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, HEPTAGON_RADIUS - BALL_RADIUS * 3)
            
            x = HEPTAGON_CENTER[0] + r * math.cos(angle)
            y = HEPTAGON_CENTER[1] + r * math.sin(angle)
            
            # 检查是否在七边形内
            if self.physics.is_point_inside(x, y):
                # 检查是否与其他球重叠
                overlap = False
                for ball in self.balls:
                    dist = math.sqrt((x - ball.x)**2 + (y - ball.y)**2)
                    if dist < ball.radius + BALL_RADIUS + 2:
                        overlap = True
                        break
                
                if not overlap:
                    # 随机初始速度
                    speed = random.uniform(50, 200)
                    angle = random.uniform(0, 2 * math.pi)
                    vx = speed * math.cos(angle)
                    vy = speed * math.sin(angle)
                    
                    ball = Ball(x=x, y=y, vx=vx, vy=vy, color=random_color())
                    self.balls.append(ball)
                    return True
        
        return False
    
    def add_ball_at(self, x: float, y: float):
        """在指定位置添加球"""
        if self.physics.is_point_inside(x, y):
            # 随机初始速度
            speed = random.uniform(50, 150)
            angle = random.uniform(0, 2 * math.pi)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            
            ball = Ball(x=x, y=y, vx=vx, vy=vy, color=random_color())
            self.balls.append(ball)
            return True
        return False
    
    def handle_events(self):
        """处理用户输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.reset_balls()
                elif event.key == pygame.K_t:
                    self.show_trails = not self.show_trails
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    self.add_ball_at(*event.pos)
    
    def update(self, dt: float):
        """更新物理状态"""
        if self.paused:
            return
        
        # 更新七边形旋转
        self.physics.update_rotation(dt)
        
        # 更新每个球的物理状态
        for ball in self.balls:
            ball.update_physics(dt)
        
        # 检测边界碰撞
        for ball in self.balls:
            self.physics.check_ball_wall_collision(ball)
        
        # 检测球与球碰撞
        self.physics.check_ball_ball_collision(self.balls)
    
    def draw(self):
        """渲染画面"""
        # 清屏
        self.screen.fill(COLOR_BLACK)
        
        # 绘制轨迹
        if self.show_trails:
            for ball in self.balls:
                if len(ball.trail) > 1:
                    # 渐变轨迹
                    points = list(ball.trail)
                    for i in range(len(points) - 1):
                        alpha = i / len(points)
                        color = (
                            int(ball.color[0] * alpha * 0.5),
                            int(ball.color[1] * alpha * 0.5),
                            int(ball.color[2] * alpha * 0.5)
                        )
                        pygame.draw.line(self.screen, color, 
                                       (int(points[i][0]), int(points[i][1])),
                                       (int(points[i+1][0]), int(points[i+1][1])), 1)
        
        # 绘制七边形
        vertices = self.physics.get_vertices()
        pygame.draw.polygon(self.screen, COLOR_HEPTAGON, 
                          [(int(v[0]), int(v[1])) for v in vertices], 2)
        
        # 绘制球
        for ball in self.balls:
            # 主体
            pygame.draw.circle(self.screen, ball.color, 
                             (int(ball.x), int(ball.y)), ball.radius)
            
            # 自旋指示器（球上的一条线）
            line_end_x = ball.x + ball.radius * 0.7 * math.cos(ball.angle)
            line_end_y = ball.y + ball.radius * 0.7 * math.sin(ball.angle)
            darker_color = (
                max(0, ball.color[0] - 80),
                max(0, ball.color[1] - 80),
                max(0, ball.color[2] - 80)
            )
            pygame.draw.line(self.screen, darker_color,
                           (int(ball.x), int(ball.y)),
                           (int(line_end_x), int(line_end_y)), 2)
        
        # 绘制UI信息
        self.draw_ui()
        
        pygame.display.flip()
    
    def draw_ui(self):
        """绘制用户界面信息"""
        # 计算平均FPS
        current_fps = self.clock.get_fps()
        self.fps_history.append(current_fps)
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        # FPS显示
        fps_text = self.font.render(f"FPS: {avg_fps:.1f}", True, COLOR_TEXT)
        self.screen.blit(fps_text, (10, 10))
        
        # 球数量
        ball_text = self.font.render(f"Balls: {len(self.balls)}", True, COLOR_TEXT)
        self.screen.blit(ball_text, (10, 35))
        
        # 旋转角度
        angle_deg = math.degrees(self.physics.rotation_angle) % 360
        angle_text = self.font.render(f"Rotation: {angle_deg:.1f}°", True, COLOR_TEXT)
        self.screen.blit(angle_text, (10, 60))
        
        # 轨迹状态
        trail_text = self.font.render(f"Trails: {'ON' if self.show_trails else 'OFF'} (T)", 
                                      True, COLOR_TEXT)
        self.screen.blit(trail_text, (10, 85))
        
        # 暂停提示
        if self.paused:
            pause_text = self.big_font.render("PAUSED", True, COLOR_WHITE)
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, 50))
            self.screen.blit(pause_text, text_rect)
        
        # 控制说明
        controls = [
            "Controls:",
            "SPACE - Pause/Resume",
            "R - Reset balls",
            "T - Toggle trails",
            "Click - Add ball",
            "ESC - Exit"
        ]
        for i, text in enumerate(controls):
            control_text = self.font.render(text, True, (100, 100, 100))
            self.screen.blit(control_text, (WINDOW_WIDTH - 160, 10 + i * 20))
    
    def run(self):
        """主循环"""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # 转换为秒
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()


# ============================================================================
# 程序入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("正七边形弹跳球物理模拟器")
    print("=" * 60)
    print("\n控制说明:")
    print("  空格键  - 暂停/恢复模拟")
    print("  R键     - 重置所有球")
    print("  T键     - 开关轨迹显示")
    print("  鼠标左键 - 在点击位置添加新球")
    print("  ESC键   - 退出程序")
    print("\n物理参数:")
    print(f"  重力加速度: {GRAVITY/100:.2f} m/s² (缩放后: {GRAVITY} px/s²)")
    print(f"  弹性系数: {RESTITUTION}")
    print(f"  旋转速度: {ROTATION_SPEED}°/s (顺时针)")
    print(f"  初始球数: {INITIAL_BALL_COUNT}")
    print("\n启动模拟...")
    print("=" * 60)
    
    simulator = HeptagonSimulator()
    simulator.run()