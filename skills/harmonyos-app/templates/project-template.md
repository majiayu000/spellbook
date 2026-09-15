# HarmonyOS Project Template

## Directory Structure

```
MyApp/
├── AppScope/
│   ├── app.json5                    # Application configuration
│   └── resources/
│       └── base/
│           └── element/
│               └── string.json      # App-level strings
├── entry/
│   ├── src/
│   │   └── main/
│   │       ├── ets/
│   │       │   ├── AbilityStage.ets      # Application entry
│   │       │   ├── abilities/
│   │       │   │   └── MainAbility.ets   # Main UIAbility
│   │       │   ├── pages/
│   │       │   │   ├── Index.ets         # Entry page
│   │       │   │   ├── Home.ets
│   │       │   │   ├── Discover.ets
│   │       │   │   └── Profile.ets
│   │       │   ├── components/           # Reusable components
│   │       │   │   ├── common/
│   │       │   │   │   ├── Header.ets
│   │       │   │   │   ├── Footer.ets
│   │       │   │   │   └── Loading.ets
│   │       │   │   └── business/
│   │       │   │       ├── UserCard.ets
│   │       │   │       └── ProductCard.ets
│   │       │   ├── viewmodels/           # State management
│   │       │   │   ├── UserViewModel.ets
│   │       │   │   └── ProductViewModel.ets
│   │       │   ├── models/               # Data models
│   │       │   │   ├── User.ets
│   │       │   │   └── Product.ets
│   │       │   ├── services/             # Business logic
│   │       │   │   ├── UserService.ets
│   │       │   │   └── ProductService.ets
│   │       │   ├── network/              # Network layer
│   │       │   │   ├── HttpClient.ets
│   │       │   │   └── ApiService.ets
│   │       │   ├── utils/                # Utilities
│   │       │   │   ├── Logger.ets
│   │       │   │   └── Constants.ets
│   │       │   └── common/               # Shared types
│   │       │       └── Types.ets
│   │       └── resources/
│   │           ├── base/
│   │           │   ├── element/
│   │           │   │   ├── string.json
│   │           │   │   └── color.json
│   │           │   ├── media/
│   │           │   └── profile/
│   │           │       └── main_pages.json
│   │           ├── en_US/                # English resources
│   │           └── zh_CN/                # Chinese resources
│   └── module.json5                      # Module configuration
├── oh_modules/                           # Dependencies
├── build-profile.json5                   # Build configuration
└── oh-package.json5                      # Package configuration
```

## Configuration Files

### app.json5

```json
{
  "app": {
    "bundleName": "com.example.myapp",
    "vendor": "example",
    "versionCode": 1000000,
    "versionName": "1.0.0",
    "icon": "$media:app_icon",
    "label": "$string:app_name"
  }
}
```

### module.json5

```json
{
  "module": {
    "name": "entry",
    "type": "entry",
    "description": "$string:module_desc",
    "mainElement": "MainAbility",
    "deviceTypes": ["phone", "tablet"],
    "deliveryWithInstall": true,
    "installationFree": false,
    "pages": "$profile:main_pages",
    "abilities": [
      {
        "name": "MainAbility",
        "srcEntry": "./ets/abilities/MainAbility.ets",
        "description": "$string:MainAbility_desc",
        "icon": "$media:icon",
        "label": "$string:MainAbility_label",
        "startWindowIcon": "$media:icon",
        "startWindowBackground": "$color:start_window_background",
        "exported": true,
        "skills": [
          {
            "entities": ["entity.system.home"],
            "actions": ["action.system.home"]
          }
        ]
      }
    ],
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET"
      }
    ]
  }
}
```

### main_pages.json

```json
{
  "src": [
    "pages/Index",
    "pages/Home",
    "pages/Discover",
    "pages/Profile"
  ]
}
```

## Core Files

### AbilityStage.ets

```typescript
import { AbilityStage, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'AbilityStage';
const DOMAIN = 0x0000;

export default class MyAbilityStage extends AbilityStage {
  onCreate(): void {
    hilog.info(DOMAIN, TAG, 'AbilityStage onCreate');
  }

  onAcceptWant(want: Want): string {
    return 'MainAbility';
  }
}
```

### MainAbility.ets

```typescript
import { UIAbility, AbilityConstant, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'MainAbility';
const DOMAIN = 0x0000;

export default class MainAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(DOMAIN, TAG, 'Ability onCreate');
  }

  onDestroy(): void {
    hilog.info(DOMAIN, TAG, 'Ability onDestroy');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    hilog.info(DOMAIN, TAG, 'Ability onWindowStageCreate');

    windowStage.loadContent('pages/Index', (err, data) => {
      if (err.code) {
        hilog.error(DOMAIN, TAG, 'Failed to load content. Cause: %{public}s', JSON.stringify(err) ?? '');
        return;
      }
      hilog.info(DOMAIN, TAG, 'Succeeded in loading content. Data: %{public}s', JSON.stringify(data) ?? '');
    });
  }

  onWindowStageDestroy(): void {
    hilog.info(DOMAIN, TAG, 'Ability onWindowStageDestroy');
  }

  onForeground(): void {
    hilog.info(DOMAIN, TAG, 'Ability onForeground');
  }

  onBackground(): void {
    hilog.info(DOMAIN, TAG, 'Ability onBackground');
  }
}
```

### Index.ets (Entry Page with Tab Navigation)

```typescript
import { router } from '@kit.ArkUI';

@Entry
@Component
struct Index {
  @State currentIndex: number = 0;

  private tabController: TabsController = new TabsController();

  @Builder
  TabBuilder(title: string, targetIndex: number, selectedImg: Resource, normalImg: Resource) {
    Column() {
      Image(this.currentIndex === targetIndex ? selectedImg : normalImg)
        .width(24)
        .height(24)
      Text(title)
        .fontSize(12)
        .fontColor(this.currentIndex === targetIndex ? '#007AFF' : '#8E8E93')
        .margin({ top: 4 })
    }
    .width('100%')
    .height(56)
    .justifyContent(FlexAlign.Center)
    .onClick(() => {
      this.currentIndex = targetIndex;
      this.tabController.changeIndex(targetIndex);
    })
  }

  build() {
    Tabs({ barPosition: BarPosition.End, controller: this.tabController }) {
      TabContent() {
        HomeTab()
      }
      .tabBar(this.TabBuilder('Home', 0, $r('app.media.home_selected'), $r('app.media.home')))

      TabContent() {
        DiscoverTab()
      }
      .tabBar(this.TabBuilder('Discover', 1, $r('app.media.discover_selected'), $r('app.media.discover')))

      TabContent() {
        ProfileTab()
      }
      .tabBar(this.TabBuilder('Profile', 2, $r('app.media.profile_selected'), $r('app.media.profile')))
    }
    .barMode(BarMode.Fixed)
    .onChange((index: number) => {
      this.currentIndex = index;
    })
  }
}

@Component
struct HomeTab {
  build() {
    Column() {
      Text('Home')
        .fontSize(24)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}

@Component
struct DiscoverTab {
  build() {
    Column() {
      Text('Discover')
        .fontSize(24)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}

@Component
struct ProfileTab {
  build() {
    Column() {
      Text('Profile')
        .fontSize(24)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}
```

## Model Template

### User.ets

```typescript
export interface User {
  id: string;
  name: string;
  email: string;
  avatar: string;
  createdAt: number;
}

export class UserModel implements User {
  id: string = '';
  name: string = '';
  email: string = '';
  avatar: string = '';
  createdAt: number = 0;

  constructor(data?: Partial<User>) {
    if (data) {
      this.id = data.id ?? '';
      this.name = data.name ?? '';
      this.email = data.email ?? '';
      this.avatar = data.avatar ?? '';
      this.createdAt = data.createdAt ?? 0;
    }
  }

  static fromJSON(json: Object): UserModel {
    return new UserModel(json as Partial<User>);
  }
}
```

## ViewModel Template

### UserViewModel.ets

```typescript
import { User, UserModel } from '../models/User';
import { UserService } from '../services/UserService';

@Observed
export class UserViewModel {
  user: User | null = null;
  isLoading: boolean = false;
  errorMessage: string = '';

  private userService: UserService = new UserService();

  async loadUser(userId: string): Promise<void> {
    this.isLoading = true;
    this.errorMessage = '';

    try {
      this.user = await this.userService.getUser(userId);
    } catch (error) {
      this.errorMessage = (error as Error).message;
    } finally {
      this.isLoading = false;
    }
  }

  async updateUser(updates: Partial<User>): Promise<void> {
    if (!this.user) return;

    this.isLoading = true;
    try {
      this.user = await this.userService.updateUser(this.user.id, updates);
    } catch (error) {
      this.errorMessage = (error as Error).message;
    } finally {
      this.isLoading = false;
    }
  }
}
```

## Service Template

### UserService.ets

```typescript
import { User, UserModel } from '../models/User';
import { ApiService } from '../network/ApiService';

export class UserService {
  private api: ApiService = new ApiService();

  async getUser(userId: string): Promise<User> {
    const response = await this.api.get<User>(`/users/${userId}`);
    return UserModel.fromJSON(response);
  }

  async updateUser(userId: string, updates: Partial<User>): Promise<User> {
    const response = await this.api.put<User>(`/users/${userId}`, updates);
    return UserModel.fromJSON(response);
  }

  async deleteUser(userId: string): Promise<void> {
    await this.api.delete(`/users/${userId}`);
  }
}
```

## Network Template

### HttpClient.ets

```typescript
import { http } from '@kit.NetworkKit';

export interface HttpResponse<T> {
  code: number;
  data: T;
  message: string;
}

export class HttpClient {
  private baseUrl: string;
  private timeout: number = 30000;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    method: http.RequestMethod,
    path: string,
    data?: Object
  ): Promise<T> {
    const httpRequest = http.createHttp();

    try {
      const response = await httpRequest.request(
        `${this.baseUrl}${path}`,
        {
          method: method,
          header: {
            'Content-Type': 'application/json'
          },
          extraData: data ? JSON.stringify(data) : undefined,
          connectTimeout: this.timeout,
          readTimeout: this.timeout
        }
      );

      if (response.responseCode >= 200 && response.responseCode < 300) {
        const result = JSON.parse(response.result as string) as HttpResponse<T>;
        return result.data;
      } else {
        throw new Error(`HTTP Error: ${response.responseCode}`);
      }
    } finally {
      httpRequest.destroy();
    }
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(http.RequestMethod.GET, path);
  }

  async post<T>(path: string, data: Object): Promise<T> {
    return this.request<T>(http.RequestMethod.POST, path, data);
  }

  async put<T>(path: string, data: Object): Promise<T> {
    return this.request<T>(http.RequestMethod.PUT, path, data);
  }

  async delete(path: string): Promise<void> {
    await this.request<void>(http.RequestMethod.DELETE, path);
  }
}
```

### ApiService.ets

```typescript
import { HttpClient } from './HttpClient';

const BASE_URL = 'https://api.example.com/v1';

export class ApiService extends HttpClient {
  constructor() {
    super(BASE_URL);
  }
}
```

## Component Template

### UserCard.ets

```typescript
import { User } from '../../models/User';

@Component
export struct UserCard {
  @Prop user: User = {} as User;
  onTap: () => void = () => {};

  build() {
    Row() {
      Image(this.user.avatar || $r('app.media.default_avatar'))
        .width(48)
        .height(48)
        .borderRadius(24)

      Column() {
        Text(this.user.name)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
        Text(this.user.email)
          .fontSize(14)
          .fontColor('#8E8E93')
          .margin({ top: 4 })
      }
      .margin({ left: 12 })
      .alignItems(HorizontalAlign.Start)

      Blank()

      Image($r('app.media.arrow_right'))
        .width(16)
        .height(16)
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Color.White)
    .borderRadius(12)
    .onClick(() => this.onTap())
  }
}
```

## Utility Templates

### Logger.ets

```typescript
import { hilog } from '@kit.PerformanceAnalysisKit';

const DOMAIN = 0x0000;

export class Logger {
  private tag: string;

  constructor(tag: string) {
    this.tag = tag;
  }

  debug(message: string, ...args: Object[]): void {
    hilog.debug(DOMAIN, this.tag, message, ...args);
  }

  info(message: string, ...args: Object[]): void {
    hilog.info(DOMAIN, this.tag, message, ...args);
  }

  warn(message: string, ...args: Object[]): void {
    hilog.warn(DOMAIN, this.tag, message, ...args);
  }

  error(message: string, ...args: Object[]): void {
    hilog.error(DOMAIN, this.tag, message, ...args);
  }
}
```

### Constants.ets

```typescript
export class Constants {
  // API
  static readonly API_BASE_URL = 'https://api.example.com/v1';
  static readonly API_TIMEOUT = 30000;

  // Storage Keys
  static readonly KEY_USER_TOKEN = 'user_' + 'token';
  static readonly KEY_USER_ID = 'user_id';
  static readonly KEY_THEME = 'app_theme';

  // UI
  static readonly ANIMATION_DURATION = 300;
  static readonly PAGE_SIZE = 20;

  // Colors
  static readonly COLOR_PRIMARY = '#007AFF';
  static readonly COLOR_SECONDARY = '#5856D6';
  static readonly COLOR_SUCCESS = '#34C759';
  static readonly COLOR_WARNING = '#FF9500';
  static readonly COLOR_ERROR = '#FF3B30';
}
```

## Resource Templates

### string.json

```json
{
  "string": [
    {
      "name": "app_name",
      "value": "MyApp"
    },
    {
      "name": "MainAbility_label",
      "value": "MyApp"
    },
    {
      "name": "MainAbility_desc",
      "value": "Main application ability"
    },
    {
      "name": "btn_submit",
      "value": "Submit"
    },
    {
      "name": "btn_cancel",
      "value": "Cancel"
    },
    {
      "name": "error_network",
      "value": "Network error. Please try again."
    }
  ]
}
```

### color.json

```json
{
  "color": [
    {
      "name": "start_window_background",
      "value": "#FFFFFF"
    },
    {
      "name": "primary",
      "value": "#007AFF"
    },
    {
      "name": "background",
      "value": "#F2F2F7"
    },
    {
      "name": "text_primary",
      "value": "#1C1C1E"
    },
    {
      "name": "text_secondary",
      "value": "#8E8E93"
    }
  ]
}
```
