import * as fs from 'fs/promises';
import * as path from 'path';

export class ProfileManager {
  private profilePath: string;

  constructor(profilePath: string) {
    this.profilePath = path.resolve(profilePath);
  }

  async ensureProfileExists(): Promise<void> {
    try {
      await fs.access(this.profilePath);
      console.log(`Profile exists at ${this.profilePath}`);
    } catch (error) {
      console.log(`Creating new profile at ${this.profilePath}`);
      await fs.mkdir(this.profilePath, { recursive: true });
      await this.createProfileStructure();
    }
  }

  private async createProfileStructure(): Promise<void> {
    const subdirs = ['Default', 'Extensions', 'Cookies'];

    for (const dir of subdirs) {
      await fs.mkdir(path.join(this.profilePath, dir), { recursive: true });
    }

    // Create basic profile files
    const profileInfo = {
      created: new Date().toISOString(),
      version: '1.0.0',
      botProfile: true
    };

    await fs.writeFile(
      path.join(this.profilePath, 'profile.json'),
      JSON.stringify(profileInfo, null, 2)
    );
  }

  getProfilePath(): string {
    return this.profilePath;
  }

  async getProfileInfo(): Promise<any> {
    try {
      const data = await fs.readFile(path.join(this.profilePath, 'profile.json'), 'utf-8');
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  async clearProfile(): Promise<void> {
    console.log(`Clearing profile at ${this.profilePath}`);

    // Remove all files except the profile.json
    const entries = await fs.readdir(this.profilePath, { withFileTypes: true });

    for (const entry of entries) {
      if (entry.name !== 'profile.json') {
        const fullPath = path.join(this.profilePath, entry.name);
        if (entry.isDirectory()) {
          await fs.rm(fullPath, { recursive: true, force: true });
        } else {
          await fs.unlink(fullPath);
        }
      }
    }

    // Recreate basic structure
    await this.createProfileStructure();
  }
}