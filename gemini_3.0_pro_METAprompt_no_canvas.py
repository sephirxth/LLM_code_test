import pygame
import math
import random
from collections import deque

# --- 配置参数 ---
WIDTH, HEIGHT = 800, 800
FPS = 60
CENTER = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)

# 几何参数
HEPTAGON_RADIUS = 300
SIDES = 7
BALL_RADIUS = 8
BALL_COUNT = 20
ROTATION_SPEED_DEG = 15  # 度/秒 (顺时针)

# 物理参数
GRAVITY = 9.81  # m/s^2
# 比例尺: 假设屏幕高度800px对应大约2米的高度，这样9.81看起来才自然
# 如果直接用9.81 px/s^2 会太慢如同漂浮。
PIXELS_PER_METER = 200  
GRAVITY_VECTOR = pygame.math.Vector2(0, GRAVITY * PIXELS_PER_METER)

RESTITUTION = 0.85  # 弹性系数 (0-1)
FRICTION = 0.995    # 空气阻力/摩擦 (简单模拟)

# 颜色库
COLORS = [
    (255, 107, 107), (24, 157, 215), (78, 205, 196), (69, 183, 209),
    (150, 206, 180), (255, 238, 173), (255, 159, 67), (84, 160, 255),
    (95, 39, 205), (200, 214, 229)
]

class Ball:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        # 随机初始速度
        self.vel = pygame.math.Vector2(random.uniform(-200, 200), random.uniform(-200, 200))
        self.radius = BALL_RADIUS
        self.color = random.choice(COLORS)
        self.mass = 1.0
        # 轨迹 (Bonus: Trail)
        self.trail = deque(maxlen=100)
    
    def update(self, dt):
        # 记录轨迹
        if len(self.trail) == 0 or (self.pos - self.trail[-1]).length_squared() > 4:
            self.trail.append(self.pos.copy())
            
        # 应用重力
        self.vel += GRAVITY_VECTOR * dt
        # 应用阻力
        self.vel *= FRICTION
        # 更新位置
        self.pos += self.vel * dt

    def draw(self, surface):
        # 绘制轨迹 (Bonus)
        if len(self.trail) > 1:
            pygame.draw.lines(surface, self.color, False, list(self.trail), 1)
        # 绘制球体
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
        # 绘制高光 (自旋效果的视觉暗示 - Bonus)
        # 这里简单画一个小点表示方向，如果有角速度会更明显
        offset = self.vel.normalize() * (self.radius * 0.5) if self.vel.length() > 0 else pygame.math.Vector2(0,0)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.pos.x + offset.x), int(self.pos.y + offset.y)), 2)

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Physics Simulation: Bouncing Balls in Rotating Heptagon")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        
        self.running = True
        self.paused = False
        self.rotation_angle = 0.0  # 当前七边形旋转角度
        
        self.balls = []
        self.init_balls()

    def init_balls(self):
        self.balls.clear()
        for _ in range(BALL_COUNT):
            self.add_ball()
            
    def add_ball(self, pos=None):
        if pos is None:
            # 在中心附近随机生成，避免生成在墙外
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, HEPTAGON_RADIUS * 0.5)
            pos_x = CENTER.x + math.cos(angle) * dist
            pos_y = CENTER.y + math.sin(angle) * dist
            self.balls.append(Ball(pos_x, pos_y))
        else:
            self.balls.append(Ball(pos[0], pos[1]))

    def get_heptagon_vertices(self):
        """计算当前旋转角度下的七边形顶点"""
        vertices = []
        angle_step = 360 / SIDES
        # 转换为弧度
        current_rad = math.radians(self.rotation_angle)
        
        for i in range(SIDES):
            # 计算每个顶点的角度
            angle_deg = i * angle_step
            angle_rad = math.radians(angle_deg) + current_rad
            
            x = CENTER.x + HEPTAGON_RADIUS * math.cos(angle_rad)
            y = CENTER.y + HEPTAGON_RADIUS * math.sin(angle_rad)
            vertices.append(pygame.math.Vector2(x, y))
        return vertices

    def resolve_ball_collision(self):
        """处理球与球之间的碰撞"""
        # 使用简单的 O(N^2) 检测，对于20个球完全足够
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                b1 = self.balls[i]
                b2 = self.balls[j]
                
                diff = b1.pos - b2.pos
                dist_sq = diff.length_squared()
                min_dist = b1.radius + b2.radius
                
                if dist_sq < min_dist ** 2 and dist_sq > 0:
                    dist = math.sqrt(dist_sq)
                    # 碰撞法线
                    n = diff / dist
                    
                    # 1. 位置修正 (防止重叠)
                    overlap = min_dist - dist
                    correction = n * (overlap * 0.5)
                    b1.pos += correction
                    b2.pos -= correction
                    
                    # 2. 动量交换
                    # 相对速度
                    rel_vel = b1.vel - b2.vel
                    vel_along_normal = rel_vel.dot(n)
                    
                    # 如果球正在远离，则不处理
                    if vel_along_normal > 0:
                        continue
                        
                    # 冲量标量 j
                    j = -(1 + RESTITUTION) * vel_along_normal
                    j /= (1/b1.mass + 1/b2.mass)
                    
                    impulse = j * n
                    b1.vel += impulse / b1.mass
                    b2.vel -= impulse / b2.mass

    def closest_point_on_segment(self, point, seg_a, seg_b):
        """寻找线段 AB 上距离点 P 最近的点"""
        ab = seg_b - seg_a
        ap = point - seg_a
        t = ap.dot(ab) / ab.length_squared()
        t = max(0, min(1, t)) # 限制在线段范围内
        return seg_a + ab * t

    def resolve_wall_collision(self, dt):
        """处理球与旋转七边形墙壁的碰撞"""
        vertices = self.get_heptagon_vertices()
        
        # 墙壁的角速度 (弧度/秒)
        # 注意：pygame y轴向下，顺时针旋转意味着角度增加
        omega = math.radians(ROTATION_SPEED_DEG)
        
        for ball in self.balls:
            for i in range(SIDES):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % SIDES]
                
                # 找到球心到墙壁线段的最近点
                closest = self.closest_point_on_segment(ball.pos, p1, p2)
                diff = ball.pos - closest
                dist = diff.length()
                
                # 碰撞检测
                if dist < ball.radius:
                    # 碰撞法线 (从墙壁指向球)
                    if dist == 0:
                        normal = (ball.pos - CENTER).normalize()
                    else:
                        normal = diff / dist
                    
                    # 1. 位置修正 (将球推出墙壁)
                    overlap = ball.radius - dist
                    ball.pos += normal * overlap
                    
                    # 2. 计算墙壁在碰撞点的速度
                    # V_wall = omega x r (2D 叉乘: (-omega * y, omega * x))
                    # 这里的 r 是相对于旋转中心(CENTER)的向量
                    r_vec = closest - CENTER
                    wall_vel = pygame.math.Vector2(-omega * r_vec.y, omega * r_vec.x)
                    
                    # 3. 相对速度计算
                    rel_vel = ball.vel - wall_vel
                    vel_along_normal = rel_vel.dot(normal)
                    
                    # 如果球已经远离墙壁，跳过
                    if vel_along_normal > 0:
                        continue
                        
                    # 4. 施加反弹冲量
                    j = -(1 + RESTITUTION) * vel_along_normal
                    ball.vel += j * normal # 这里的 ball.vel 更新包含了 wall_vel 的影响，因为是从相对速度算回来的
                    
                    # 简单摩擦/切向阻力 (可选，防止无限加速)
                    # tangent = pygame.math.Vector2(-normal.y, normal.x)
                    # ball.vel -= tangent * ball.vel.dot(tangent) * 0.1

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # 秒
            
            # --- 事件处理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.init_balls()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # 左键点击
                        self.add_ball(pygame.mouse.get_pos())

            if not self.paused:
                # --- 更新逻辑 ---
                # 1. 更新旋转角度 (顺时针)
                self.rotation_angle += ROTATION_SPEED_DEG * dt
                self.rotation_angle %= 360
                
                # 2. 更新球的物理状态
                # 子步模拟 (Sub-stepping) 以提高碰撞稳定性
                sub_steps = 4
                dt_step = dt / sub_steps
                
                for _ in range(sub_steps):
                    for ball in self.balls:
                        ball.update(dt_step)
                    
                    self.resolve_ball_collision()
                    self.resolve_wall_collision(dt_step)

            # --- 渲染逻辑 ---
            self.screen.fill((20, 20, 20)) # 深灰色背景
            
            # 绘制七边形
            verts = self.get_heptagon_vertices()
            pygame.draw.polygon(self.screen, (200, 200, 200), verts, 3)
            
            # 绘制球
            for ball in self.balls:
                ball.draw(self.screen)
            
            # UI 信息
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (255, 255, 255))
            info_text = self.font.render(f"Balls: {len(self.balls)} | Space:Pause R:Reset", True, (150, 150, 150))
            self.screen.blit(fps_text, (10, 10))
            self.screen.blit(info_text, (10, 30))

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    sim = Simulation()
    sim.run()