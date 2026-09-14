import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { finalize } from 'rxjs';

interface Animal {
  id: number;
  name: string;
  habitat: string;
  diet: string;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly http = inject(HttpClient);
  readonly animals = signal<Animal[]>([]);
  readonly loading = signal(false);
  readonly error = signal('');

  constructor() {
    this.refresh();
  }

  refresh(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.http
      .get<Animal[]>('/api/animals')
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (animals) => this.animals.set(animals),
        error: () => this.error.set('De dieren konden niet worden opgehaald. Probeer het opnieuw.'),
      });
  }
}
